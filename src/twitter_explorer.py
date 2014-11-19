import datetime
import tweepy
import time
import re
import urllib2
from tld import get_tld
from tld.utils import update_tld_names
import timeit

import sys
import os
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'Frontend')))

os.environ['DJANGO_SETTINGS_MODULE'] = 'Frontend.settings'

from tweets.models import*
from tweets.models import Keyword as T_keyword
from explorer.models import*
from explorer.models import Keyword as E_keyword


__author__ = "ACME: CSCC01F14 Team 4"
__authors__ = "Yuya Iwabuchi, Jai Sughand, Xiang Wang, Kyle Bridgemohansingh, Ryan Pan"

# Twitter Developer API
CONSUMER_KEY = "UITySH5N4iGOE3l6C0YgmwHVd"
CONSUMER_SECRET = "H7lXeLBDQv3o7i4wISGJtukdAqC6X9Vr4EXTdaIAVVrN56Lwbh"
ACCESS_TOKEN = "2825329492-TKU4s0Mky7vazr60WKHQV7R6sJT2wYE4ysR3Gm3"
ACCESS_TOKEN_SECRET = "I740fF6x6v0srzbY7LCAjNWXXOzZRMBFbkoiwZ5FgqC5s"

# Globals to be used for Database
STORE_ALL_SOURCES = False
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

INIT_TWEET_COUNT=1000
ITER_TWEET_COUNT=100

FROM_START = True  
MIN_ITERATION_TIME = 600
#Seconds to wait before retrying call
WAIT_RATE = (60 * 1) + 0

# Used for commmunication stream
COMM_FILE = '_comm.stream'
RETRY_COUNT = 10
RETRY_DELTA = 1
SLEEP_TIME = 5


def authorize():
    """ (None) -> tweepy.API
    Will use global keys to allow use of API
    """
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    return tweepy.API(auth)

def rate_reached():
    """ (None) -> None
    Helper function to be called when a rate limit has been reached.
    """
    print ('Twitter Rate Limit Reached, Attempting to Continue.')
    print ('Resuming in ' + str(int(WAIT_RATE/60)) + ' minute(s) and '
                   + str(WAIT_RATE % 60) + ' second(s).')
    time.sleep(WAIT_RATE)

def get_tweets(screen_name, amount):
    """ (str, [int]) -> list of list
    Gets amount tweets from specified users
    Returns list in format [uni tweet, uni user, str time_tweeted]

    Keyword arguments:
    screen_name     -- string of twitter handle
    sites           -- List of string site urls to look for
    """
    api = authorize()
    rate_reached = True
    while rate_reached:
        try:
            user = api.get_user(screen_name)
            rate_reached = False
        except:
            rate_reached()

    tweets = []
    last_id = -1
    #incase user asks for more tweets than available
    while len(tweets) < amount and len(tweets) != user.statuses_count:
        #check how many more tweets is needed
        count = amount - len(tweets)
        try:
            new_tweets = api.user_timeline(screen_name=screen_name, count=count)

            #If there are no more tweets, finish
            if not new_tweets:
                break
            #Add new tweets
            for tweet in new_tweets:
                tweets.append(tweet)
            last_id = tweets[-1].id
        except:
            rate_reached()
        return tweets



def get_follower_count(screen_name):
    """ (str) -> int
    Gets number of followers of screen_name's account

    """
    api = authorize()
    while True:
        try:
            user = api.get_user(screen_name)
            return user.followers_count
        except:
            rate_reached()

def get_keywords(tweet, keywords):
    """ (status, list of str) -> list of str
    Searches and returns keywords contained in the tweet
    Returns empty list otherwise.

    Keyword arguments:
    tweet           -- Status structure to be searched through
    sites           -- List of keywords to look for
    """
    for key in keywords:
        if re.search(key, tweet.text.encode('utf8'), re.IGNORECASE):
            matched_keywords.append(key)

    #Uses get_sources, but instead of searching tweets, searches

    matched_keywords_in_urls = get_sources(tweet, keywords)

    return matched_keywords + matched_keywords_in_urls


def get_sources(tweet, sites):
    """ (status, list of str) -> list of str
    Searches and returns links redirected to sites within the urls
    of the tweet
    Returns empty list if none found

    Keyword arguments:
    tweet           -- Status structure to be searched through
    sites           -- List of site urls to look for
    """
    matched_urls = []
    expanded_urls = ''
    display_urls = ''
    for url in tweet.entities['urls']:
        try:
            # tries to get full url on shortened urls
            expanded_urls += urllib2.urlopen(url['expanded_url']).geturl() + ' '
            expanded_urls += urllib2.urlopen(url['display_url']).geturl() + ' '
        except:
            expanded_urls += url['expanded_url'] + ' '
            display_urls += url['display_url'] + ' '

    #substring, expanded includes scheme, display may not
    for site in sites:
        if re.search(key, expanded_url), re.IGNORECASE) or
         re.search(key, display_url, re.IGNORECASE):
            matched_urls.append(site)

    return matched_urls

def parse_tweets(twitter_users, keywords, foreign_sites, tweet_number):
    """ (list of str, list of str, list of str, str) -> none
    Parses through tweets of users, looking for keywords and foreign sites.
    Relevant tweets will be sent to a database.

    Keyword arguments:
    twitter_users   -- List of strings as twitter handles
    keywords        -- List of strings as keywords to search for
    foreign_sites   -- List of strings as sources to search for
    db_name         -- String of Database
    """
    django.setup()
    added, updated, no_match = 0, 0, 0
    start = time.time()

    for user in twitter_users:
        print "Parsing @" + user
        tweets = get_tweets(user, tweet_number)
        tweet_followers = get_follower_count(user)

        for tweet in tweets:
            print '\tEvaluating ...\r'
            tweet_id = tweet.id
            tweet_date = str(tweet.created_at)
            tweet_user = tweet.user.screen_name
            tweet_store_date = datetime.datetime.now().strftime(DATE_FORMAT)
            tweet_keywords = get_keywords(tweet, keywords)
            tweet_sources = get_sources(tweet, foreign_sites)
            tweet_text = tweet.text

            print "\tTweet:    ", tweet.text
            print "\tAuthor:   ", tweet_user
            print "\tDate:     ", tweet_date
            print "\tKeywords: ", tweet_keywords
            print "\tSources:  ", tweet_sources
            print "\n"

            if not(tweet_keywords == [] and (tweet_sources ==[] or STORE_ALL_SOURCES)):

                tweet_list = Tweet.objects.filter(tweet_id = tweet_id)
                if (not tweet_list): 

                    tweet = Tweet(tweet_id = tweet_id, user=tweet_user, date_added = tweet_store_date, date_published = tweet_date, followers = tweet_followers, text=tweet_text )
                    tweet.save()


                    tweet =  Tweet.objects.get(tweet_id=tweet_id)
                    
                    for key in tweet_keywords:
                        tweet.keyword_set.create(keyword = key)
       

                    for source in tweet_sources:
                        tweet.source_set.create(source = source)

                    added += 1
                    print "\tResult:    Match detected! Added to the database."

                else:

                    tweet = tweet_list[0]
                    tweet.tweet_text= tweet_text
                    tweet.tweet_id = tweet_id
                    tweet.user = tweet_user 
                    tweet.date_added = tweet_store_date
                    tweet.date_published = tweet_date
                    tweet.followers = tweet_followers
                    tweet.save()

                    for key in tweet_keywords:
                        if not T_keyword.objects.filter(keyword = key): 
                            tweet.keyword_set.create(keyword = key)

                    for source in tweet_sources:
                        if not Source.objects.filter(source = source):
                            tweet.source_set.create(source = source)
                    print "\tResult:    Match detected! Tweet already in database. Updating."
                    updated += 1

            else:
                no_match += 1
                print "\tResult:    No Match Detected."
        print("\n\tStatistics\n\tAdded: %i | Updated: %i | No Match: %i | Time Elapsed: %is" %
          (added, updated, no_match, time.time() - start))
        print "+--------------------------------------------------------------------+"

    print("Finished parsing all users!")


def explore(accounts_db, keyword_db, site_db, tweet_number):
    """ (str, str, str, str) -> None
    Connects to accounts, keyword and site database, crawls within monitoring sites,
    then pushes articles which matches the keywords or foreign sites to the tweet database

    Keyword arguments:
    accounts_db         -- Twitter Accounts database name
    keyword_db          -- Keywords database name
    site_db             -- Sites database name
    tweet_db            -- Tweet database name
    """
    print "+----------------------------------------------------------+"
    print "| Retrieving data from Database ...                        |"
    print "+----------------------------------------------------------+"

    # Connects to Site Database


    monitoring_sites = []
    msites = Msite.objects.all()
    # Retrieve, store, and print monitoring site information
    print "\nMonitoring Sites\n\t%-25s%-40s" % ("Name", "URL")
    for site in msites:
        # monitoring_sites is now in form [['Name', 'URL'], ...]
        monitoring_sites.append([site.name, site.url])
        print("\t%-25s%-40s" % (site.name, site.url))

    foreign_sites = []
    # Retrieve, store, and print foreign site information
    fsites = Fsite.objects.all()
    print "\nForeign Sites\n\t%-25s%-40s" % ("Name", "URL")
    for site in fsites:
        # foreign_sites is now in form ['URL', ...]
        foreign_sites.append(site.url)
        print("\t%-25s%-40s" % (site.name, site.url))


    # Retrieve all stored keywords
    keywords = E_keyword.objects.all()
    keyword_list = []

    # Print all the keywords
    print "\nKeywords:"

    for key in keywords:
        keyword_list.append(str(key.keyword))
        print "\t%s" % key.keyword

    print "\n"

    print "+----------------------------------------------------------+"
    print "| Populating Accounts ...                                  |"
    print "+----------------------------------------------------------+"

    # Retrieve all stored Accounts
    accounts = Taccount.objects.all()
    accounts_list = []




    # Print all the Accounts
    print "\nTwitter Accounts:"
    for account in accounts:
        accounts_list.append(str(account.account))
        print "\t%s" % account.account


    print "\n"

    print "+----------------------------------------------------------+"
    print "| Evaluating Tweets ...                                    |"
    print "+----------------------------------------------------------+"
    # Parse the articles in all sites
    parse_tweets(accounts_list, keyword_list, foreign_sites, tweet_number)

def comm_write(text):
    for i in range(RETRY_COUNT):
        try:
            comm = open('twitter' + COMM_FILE, 'w')
            comm.write(text)
            comm.close()
            return None
        except:
            time.sleep(RETRY_DELTA)

def comm_read():
    for i in range(RETRY_COUNT):
        try:
            comm = open('twitter' + COMM_FILE, 'r')
            msg = comm.read()
            comm.close()
            return msg
        except:
            time.sleep(RETRY_DELTA)

def comm_init():
    comm_write('RR')

def check_command():
    msg = comm_read()

    if msg[0] == 'W':
        command = msg[1]
        if command == 'S':
            print ('Stopping Explorer...')
            comm_write('SS')
            sys.exit(0)
        elif command == 'P':
            print ('Pausing ...')
            comm_write('PP')
            while comm_read()[1] == 'P':
                print ('Waiting %i seconds ...' % SLEEP_TIME)
                time.sleep(SLEEP_TIME)
            check_command()
        elif command == 'R':
            print ('Resuming ...')
            comm_write('RR')

if __name__ == '__main__':
    pass
    # parse_tweets(['CNN', 'TIME'], ['obama','hollywood', 'not', 'fire', 'president', 'activities'], ['http://cnn.com/', 'http://ti.me'], 'tweets')
    #
    #  Initialize Communication Stream
    # comm_init()
    #
    # fs = FROM_START
    #
    # while 1:
    #     # Check for any new command on communication stream
    #     check_command()
    #
    #     start = timeit.default_timer()
    #     if (fs == True ):
    #         explore('taccounts', 'keywords', 'sites', INIT_TWEET_COUNT)
    #         fs = False
    #     else:
    #         explore('taccounts', 'keywords', 'sites', ITER_TWEET_COUNT)
    #
    #     end = timeit.default_timer()
    #     delta_time = end - start
    #     time.sleep(max(MIN_ITERATION_TIME-delta_time, 0))
