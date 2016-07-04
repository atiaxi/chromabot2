import logging
import random
import re
import socket
import string
import time
from urllib.parse import quote_plus

import praw
from retrying import retry
from requests.exceptions import ConnectionError, HTTPError, Timeout

from .commands import Result
from .models import User
from .outsiders import Message, NullOutsider, outsider
from .utils import col_to_letter


def base36decode(number):
    return int(number, 36)


def is_reddit_exception(ex):
    logging.warning("Caught exception %s", ex)
    return isinstance(ex, (
        praw.errors.APIException,
        praw.errors.HTTPException,
        ConnectionError,
        HTTPError,
        Timeout,
        socket.timeout,
        socket.error,
    ))

FAIL_NOT_PLAYER = """
Hello!  I'm a bot, in charge of running the 'Chroma' reddit game.
Unfortunately, you don't seem to actually be playing the game I run!
If you'd like to change that, comment in the latest recruitment thread
in /r/%s"""

INVASION = """
Reports of troops bound to this location have been flooding in.  As the
air-raid sirens blare and the civilians make their ways to the bomb shelters,
you know you have only a limited amount of time to prepare.

Your best intelligence indicates that the invasion will begin at
{time}.
"""

BATTLE = """
# Battle {id}

### Score: {team0} vs {team1}

{board}

This battle will end sometime near {end}.  To fight, comment here with your
commands, prefixed with `>`.
"""

END_OF_BATTLE = """
# Battle {id}: COMPLETE

### Score: {team0} vs {team1}
## The victor: {winner}

{board}
"""

EXP_MULTIPLIER = 1000
EXP_MAX = 54000

retryable = retry(retry_on_exception=is_reddit_exception,
                  wait_exponential_multiplier=EXP_MULTIPLIER,
                  wait_exponential_max=EXP_MAX)


def timestr(secs=None):
    if secs is None:
        secs = time.mktime(time.localtime())

    timeresult = time.gmtime(secs)
    timestresult = time.strftime("%Y-%m-%d %I:%M:%S %p GMT", timeresult)
    url = ("http://www.wolframalpha.com/input/?i=%s+in+local+time" %
           quote_plus(timestresult))
    return "[%s](%s)" % (timestresult, url)


def extract_command(text, use_full=False):
    text = text.strip()
    regex = re.compile(r"(?:\n|^)>(.*)")
    result = regex.findall(text)
    if use_full and not result:
        return [text]
    return result


def reddit_data(battle):
    return battle.load_outside_data()['reddit']


class RedditMessage(Message):
    def __init__(self, raw_text, issuer, outside, actual=None):
        super().__init__(raw_text, issuer, outside)
        self.actual = actual

    @retryable
    def reply(self, text):
        if self.actual:
            self.actual.reply(text)
        else:
            logging.warning("Could not reply to message because no actual")


@outsider("reddit")
class RedditOutsider(NullOutsider):

    def __init__(self, config):
        super().__init__(config)
        if 'reddit' not in config:
            logging.critical("Config file needs a [reddit] section!")
            raise ValueError("Could not load reddit config")
        ua = config.reddit['useragent']
        site = config.reddit.get('site', 'reddit')
        logging.debug("Using ua '%s' and site '%s'", ua, site)
        self.reddit = praw.Reddit(user_agent=ua, site_name=site)

    @retryable
    def startup(self):
        conf = self.config
        username = conf.reddit['username']
        passwd = conf.reddit['password']
        logging.info("Logging in as %s", username)
        logging.debug("Using password: %s", passwd)
        self.reddit.login(username, passwd)
        logging.info("Logged in")

    @retryable
    def handle_recruits(self):
        conf = self.config
        hq = self.reddit.get_subreddit(self.config.reddit['headquarters'])
        submissions = hq.get_new()
        for submission in submissions:
            if "[recruitment]" in submission.title.lower():
                self.recruit_from_post(submission)
                break  # Only recruit from the first one

    @retryable
    def recruit_from_post(self, post):
        post.replace_more_comments(threshold=0)
        flat_comments = praw.helpers.flatten_tree(post.comments)
        for comment in flat_comments:
            self.recruit_from_comment(comment)

    @retryable
    def recruit_from_comment(self, comment):
        if not comment.author:  # Deleted comments don't have an author
            return
        name = comment.author.name.lower()
        if name == self.config.reddit['username'].lower():
            return

        # Is this author already one of us?
        with self.db.session() as s:
            found = s.query(User).filter_by(name=name).first()
        if not found:
            # Getting the author ID triggers a lookup on the userpage.  In the
            # case of banned users, this will 404.  Normally that would be
            # retried by @retryable, but since that comment's not going
            # anywhere, we'd get stuck in a loop:
            try:
                author_id = comment.author.id
            except praw.errors.NotFound:
                logging.warning("Ignored banned user %s" % name)
                return

            assignment = self.config.reddit['assignment']
            if assignment == 'uid':
                base10_id = base36decode(author_id)
                team = base10_id % 2
            elif assignment == "random":
                team = random.randint(0, 1)
            else:
                logging.critical("Don't understand how to assign via %s",
                                 assignment)
                team = 0
            newbie = User.create(
                db=self.db,
                name=name,
                team=team,
                leader=True,
            )
            logging.info("Recruited %s to team %s", newbie, team)
            reply = "You've been recruited!  Welcome to team %d." % team
            comment.reply(reply)

    def status_for(self, user):
        report = [
            "Hello {name}!",
            "You are a {rank} of the {team} army. "
            "Your troops are as follows:"
        ]
        report.extend(self.troop_status(troop) for troop in user.troops)
        result = "\n\n".join(report)
        return result.format(
            name=user.name,
            rank=user.leader,
            team=user.team,
        )

    def troop_status(self, troop):
        result = [
            "*",
            troop.type.capitalize() + ":",
        ]
        if troop.is_deployable():
            battle = "Ready for battle"
        elif troop.is_alive():
            battle = "In battle #{id} at {col},{row}"
            display_row = troop.row + 1
            data = dict(id=troop.battle.id,
                        col=col_to_letter(troop.col),
                        row=display_row)
            battle = battle.format(**data)
        else:
            battle = troop.cause_of_death
        result.append(battle)
        return " ".join(result)

    @retryable
    def find_player(self, comment):
        if comment.author:  # Some messages (mod invites) don't have authors
            with self.db.session() as session:
                player = session.query(User).filter_by(
                    name=comment.author.name.lower()).first()
            if not player and getattr(comment, 'was_comment', None):
                comment.reply(FAIL_NOT_PLAYER %
                              self.config.headquarters)
            return player
        return None

    @retryable
    def get_messages(self):
        # For now, just PMs
        unread = self.reddit.get_unread(True, True)
        result = []
        for comment in unread:
            logging.info("Received message %s" % comment.body)
            # Only PMs, we deal with comment replies in process_post_for_battle
            if not comment.was_comment:
                # TODO: Check if we've seen this comment already
                player = self.find_player(comment)
                if player:
                    cmds = extract_command(comment.body, use_full=True)
                    logging.debug("CMDS is `%s` " % cmds)
                    result.extend(
                        RedditMessage(cmd, player, self, comment)
                        for cmd in cmds
                    )

                comment.mark_as_read()
        return result

    @retryable
    def populate_battle_data(self, battle, data):
        from .utils import now
        when = timestr(battle.begins)

        text = INVASION.format(time=timestr(battle.begins))
        post = self.reddit.submit(self.config.reddit['disputed_zone'],
                                  title='The Eternal Battle Continues',
                                  text=text)
        _, _, id36 = post.name.partition('_')
        data['reddit'] = {
            'fullname': post.name,
            'id36': id36,
        }

    @retryable
    def report_results(self, results):
        for result in results:
            if not result.is_internal():
                result.message.reply(result.text)

    @retryable
    def update_battle(self, battle):
        board = self.visual_state(battle)
        team0, team1, *_ = battle.load_scores()
        end = timestr(battle.display_ends)
        text = BATTLE.format(id=battle.id, team0=team0, team1=team1,
                             board=board, end=end)

        post = self.reddit.get_submission(
            submission_id=reddit_data(battle)['id36'],
        )
        post.edit(text)

    @retryable
    def report_battle_end(self, battle):
        board = self.visual_state(battle)
        team0, team1, *_ = battle.load_scores()
        winner = "Team %s" % battle.victor
        text = END_OF_BATTLE.format(id=battle.id, team0=team0, team1=team1,
                                    board=board, winner=winner)
        post = self.reddit.get_submission(
            submission_id=reddit_data(battle)['id36'],
        )
        post.edit(text)


    def visual_state(self, battle):
        board = battle.realize_board()
        num_cols = len(board[0])
        num_rows = len(board)
        col_labels = " " + string.ascii_uppercase[:num_cols]
        header = "|%s|" % "|".join(col_labels)
        sep = "|%s" % ("-|" * len(col_labels))
        lines = [header, sep]
        for row_number, row in enumerate(board):
            cols = ["%d" % (row_number + 1)]
            cols.extend(self.icon_for_troop(troop) for troop in row)
            lines.append("|%s|" % "|".join(cols))
        return "\n".join(lines)
