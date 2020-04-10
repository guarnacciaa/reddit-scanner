#!/usr/bin/python3

import re
import csv
import ssl
import sys
import praw
import smtplib
import requests
from datetime import datetime, timezone


# RedditScanner Configuration
version = '1.1'
storage_file = 'reddit-scanner.db'
storage_retention = 1296000

# Reddit Configuration
reddit_client_id = '<Insert Reddit Client ID>'
reddit_secret = '<Insert Reddit Secret>'
reddit_user_agent = 'python:com.andreaguarnaccia.reddit-scanner:v' + \
    version + ' (by /u/valniro)'
reddit_subreddit_name = '<Insert Subreddit Name (i.e.: all)'
reddit_search_words = ['<Insert String 1>', '<Insert String 2>']

# Gmail Configuration
gmail_server = 'smtp.gmail.com'
gmail_port = 465
gmail_user = 'your_user@gmail.com'
gmail_password = 'password'
gmail_sender = 'RedditScanner <user@gmail.com>'
gmail_receiver = '<Insert Recipient Mail>'
gmail_subject = '[RedditScanner] We got some matched posts'

# Telegram Configuration
telegram_enabled = True
telegram_token = '<Insert Telegram Token>'
telegram_id = '<Insert Telegram ID>'


# Main
current_epoch = int(datetime.utcnow().timestamp())

reddit = praw.Reddit(client_id=reddit_client_id,
                     client_secret=reddit_secret,
                     user_agent=reddit_user_agent)

subreddit = reddit.subreddit(reddit_subreddit_name)

storage_hash = dict()
try:
    storage = open(storage_file, "r")

    for line in storage:
        fields = [x.strip() for x in line.split(',')]
        storage_hash[fields[0]] = fields[1]

    storage.close()
except OSError as err:
    print("OS error: {0}".format(err))
except ValueError:
    print("Could not convert data to an integer.")
except:
    print("Unexpected error:", sys.exc_info()[0])
    raise

match = {}

for submission in subreddit.new():
    for word in reddit_search_words:
        if (re.search(word, submission.title, re.IGNORECASE)):
            if submission.id not in storage_hash:
                match[submission.id] = {}
                match[submission.id]['timestamp'] = submission.created_utc
                match[submission.id]['title'] = re.sub(r'({})'.format(word), r'<b><font color="red">\1</font></b>',
                                                       submission.title, flags=re.I)
                match[submission.id]['title'] = re.sub(
                    u"\u2013", "-", match[submission.id]['title'])
                match[submission.id]['url'] = submission.url
                storage_hash[submission.id] = submission.created_utc

if bool(match):
    if (gmail_enabled):
        dump = ''

        for reddit_id in match:
            dump += '<ul><li>Timestamp: ' +\
                str(datetime.fromtimestamp(
                    match[reddit_id]['timestamp'])) + '</li>\n'
            dump += '<li>ID: ' + reddit_id + '</li>\n'
            dump += '<li>Title: ' + match[reddit_id]['title'] + '</li>\n'
            dump += '<li>URL  : ' + match[reddit_id]['url'] + '</li></ul>\n\n'

        context = ssl.create_default_context()

        server = smtplib.SMTP_SSL()
        server.connect(gmail_server, gmail_port)
        server.ehlo()
        server.login(gmail_user, gmail_password)

        gmail_message = """From: """ + gmail_sender + """
To: """ + gmail_receiver + """
MIME-Version: 1.0
Content-type: text/html
Subject: """ + gmail_subject + """


<h1>List of matches:</h1>
<br />
""" + dump
        server.sendmail(gmail_sender, gmail_receiver, gmail_message)

        try:
            storage = open(storage_file, "w")

            for item in storage_hash:
                if int(storage_hash[item]) > (current_epoch - storage_retention):
                    storage.write(
                        item + ',' + str(int(storage_hash[item])) + '\n')

            storage.close()
        except OSError as err:
            print("OS error: {0}".format(err))
        except ValueError:
            print("Could not convert data to an integer.")
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    if (telegram_enabled):
        for reddit_id in match:
            telegram_text = 'https://api.telegram.org/bot' + telegram_token + '/sendMessage?chat_id=' + \
                telegram_id + '&parse_mode=Markdown&text=' + \
                match[reddit_id]['url']
            response = requests.get(telegram_text)
