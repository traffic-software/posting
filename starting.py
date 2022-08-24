from email.policy import SMTP

import threading
import time
import shutil
import random
import string
import fnmatch
import sys
from os import path

from pyvirtualdisplay import Display
from datetime import datetime
import smtp
from ps_lib.browser import browser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.ps_str import ps_str
from ps_lib.imap import imap
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import os
from selenium.webdriver.support.select import Select

import re

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))



def main(account_data, postinfo, packages_id, body_mail):
    # work start time


    starttime = datetime.now()
    print(account_data)
    postinfo = postinfo.get_post(account_data['id'])

    print(postinfo)



    print(datetime.now().strftime("%H:%M:%S"))

    account_id = account_data['id']
    worker_acc = accounts()
    settings = table()


    b = browser(account_id, pva=account_data)


    time.sleep(5)
    # if b.PROXY_PASS == False:
    #     b.exit()
    #     print('proxy condition not fulfilled')
    #     # worker_acc.ban_3(account_id, 5)
    #     time.sleep(10)
    #     return False

    #start your work
    try:

        b.get_url('https://www.facebook.com')
    except:
        b.exit()

    faceboo_create_new_account = b.find("//a[@class='_42ft _4jy0 _6lti _4jy6 _4jy2 selected _51sy']",'Facebook link')
    faceboo_create_new_account.click()
    day = Select(b.find("day","tag","id"))
    # facebook_birthday.click()
    day.select_by_visible_text("20")



    # google = b.find("//input[@class='gLFyf gsfi']",'google link')
    # google.send_keys(account_data['email'])
    # google.send_keys(Keys.ENTER)

    # b.find("//div[@class='comment-form wow fadeIn animated']//input[@name='email']")
    # b.finds("//div[@class='comment-form wow fadeIn animated']//input[@name='email']")
    # b.one(perentelemtnt,"//div[@class='comment-form wow fadeIn animated']//input[@name='email']")
    # b.afew(perentelemtnt,"//div[@class='comment-form wow fadeIn animated']//input[@name='email']")

    print('browser close')
    b.ipinfo_save(software_name='google')

    print('start :', starttime)
    print('end :', datetime.now().strftime("%H:%M:%S"))



setup = table()
setup.token_verify()
packages_id = '317345'

worker = 2
# ........................start worker....................

utility = helper()
headers = {}
profile_ids = {}
acc = accounts()
post = post()
if sys.platform not in ['Windows', 'win32', 'cygwin']:
    display = Display(visible=0, size=(1024, 768))
    display.start()

while True:
    if setup.token_off():
        print('software off now but reply checking runing')
        time.sleep(60)
        continue
    one_account = acc.get_account()
    if one_account == None:
        print('account not find for worker')
        time.sleep(60)
        continue
    postinfo = post.get_post(one_account['id'])
    body_mail = None
    if postinfo == None:

        print('post not find for worker')
        time.sleep(10)
        continue
    print('account last use time is : ', one_account['last_updates'])

    if path.isdir('profiles/' + str(one_account['id'])) == True:
        shutil.rmtree('profiles/' + str(one_account['id']))

    print('main')
    main(one_account, post, packages_id, body_mail)
    time.sleep(10)