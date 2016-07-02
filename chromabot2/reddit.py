import logging
import random
import socket

import praw
from retrying import retry
from requests.exceptions import ConnectionError, HTTPError, Timeout

from .commands import Result
from .models import User
from .outsiders import outsider, NullOutsider


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

EXP_MULTIPLIER = 1000
EXP_MAX = 54000

retryable = retry(retry_on_exception=is_reddit_exception,
                  wait_exponential_multiplier=EXP_MULTIPLIER,
                  wait_exponential_max=EXP_MAX)


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
                logging.warning("Don't understand how to assign via %s",
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
