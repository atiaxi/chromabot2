#!/usr/bin/env python
import argparse
import logging

import praw

from chromabot2.config import Config

# Step by step guide on how to get the relevant oauth information.
#
# 1:  Create an account you want to use for the bot
# 2:  Create an 'app' with that account.
#       See http://praw.readthedocs.io/en/stable/pages/oauth.html#step-1-create-an-application
# 3:  Fill in the values in the conf file for:
#       3a:  The client ID as 'client_id'
#       3b:  The client secret as 'client_secret'
#       3c:  The redirect URI as 'redirect_uri'
# 4:  Run this script, pointing to that config file:
#       ./bin/oauth.py -c config/local.ini  # For example
# 5:  You'll be given a link (starting with 'The auth url is:').  Go to it.
# 6:  Give the app full permissions to use the bot account.
# 7:  You'll be redirected back to a broken page.  The URL will look like:
#       http://lvh.me:8000/redirect?state=uniqueKey&code=ACXmq3UFWMDkW7Q83cQP9heizqM
# 8:  Copy the code at the end of the URL.  This is your 'auth key'
#       8a:  Enter this in the conf file as 'access_code'
# 9:  Run this script again, with the auth key:
#       ./bin/oauth.py -c config/local.ini -a ACXmq3UFWMDkW7Q83cQP9heizqM
# 10: You'll be given a line starting with "REFRESH TOKEN IS".  That is your
#     refresh token.
#       10a:  Enter this in the conf file as 'refresh_token'
# Done!


# Adapted from:
# https://www.reddit.com/r/GoldTesting/comments/3cm1p8/how_to_make_your_bot_use_oauth2/


def main():

    argp = argparse.ArgumentParser()
    argp.add_argument("-c", "--conf",
                      default=None,
                      help="Configuration file location")
    argp.add_argument('-a', '--auth',
                      default=None,
                      help="Auth key")
    argp.add_argument("-r", "--refresh",
                      default=None,
                      help="Refresh token")
    args = argp.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    config = Config(args.conf)

    ua = config.reddit['useragent']
    site = config.reddit.get('site', 'reddit')
    reddit = praw.Reddit(user_agent=ua, site_name=site)
    logging.debug("Connecting to %s as %s", site, ua)
    reddit.set_oauth_app_info(
        client_id=config.reddit['client_id'],
        client_secret=config.reddit['client_secret'],
        redirect_uri=config.reddit['redirect_uri'],
    )
    if args.refresh:
        reddit.refresh_access_information(args.refresh)
        print("You are ", reddit.get_me())
    elif args.auth:
        access_information = reddit.get_access_information(args.auth)
        print(
            "REFRESH TOKEN IS %s" % access_information['refresh_token'])
    else:
        scopes = (
            "account creddits edit flair history identity livemanage modconfig "
            "modcontributors modflair modlog modothers modposts modself "
            "modwiki mysubreddits privatemessages read report save submit "
            "subscribe vote wikiedit wikiread"
        )
        url = reddit.get_authorize_url('uniqueKey', scopes, True)
        if site != 'reddit':
            url = url.replace("www.reddit.com", site)
        print("The auth url is: %s", url)


if __name__ == "__main__":
    main()
