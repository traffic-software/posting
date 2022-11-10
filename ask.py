from email.policy import SMTP
from re import sub
import threading
import time
import shutil
import random
import string
import fnmatch
import sys
from os import path
from weakref import proxy
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
import os
# import pyautogui
import re

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))


def main(account_data, postinfo, packages_id, body_mail):
    # work start time
    starttime = datetime.now().strftime("%H:%M:%S")

    print(datetime.now().strftime("%H:%M:%S"))

    account_id = account_data['id']
    print("account id: ", account_id)
    print(account_data)
    print(postinfo.get_post(account_data['id']))
    worker_acc = accounts()
    settings = table()
    worker_token = worker_acc.get_token(account_data)
    print(worker_token)
    

    b = browser(account_id, pva=account_data)
    time.sleep(5)
    # if b.PROXY_PASS == False:
    #     b.exit()
    #     print('proxy condition not fulfilled')
    #     # worker_acc.ban_3(account_id, 5)
    #     time.sleep(10)
    #     return False

    try:

        b.get_url('https://www.google.com')
    except:
        b.exit()
    # time.sleep(240)
    while True:
        worker_keyword = worker_acc.get_ask_keyword(account_data, worker_token)

        q = b.select_element_xpath('//input[@name="q"]', 'form')
        print(q.get_attribute('innerHTML'))

        if worker_keyword == None:
            print('no keyword')
            continue
        q.clear()
        print(worker_keyword['keyword'])
        for character in worker_keyword['keyword']:

            q.send_keys(character)

        q.send_keys(Keys.ENTER)
        # time.sleep(120)

        try:
            center_col = b.select_element_xpath(
                '//*[@id="center_col"]', 'center_col')
        except:
            b.exit()
            return False

        # loing tail keyowrd

        arg = b.element_xpath(center_col, '//*[@id="botstuff"]', 'botstuff')
        keywords = b.afew(elements=arg, selector="a", bytype='tag')
        related_keywords = []
        for item in keywords:
            related_keywords.append(item.text)

        # RELATED_QUESTION

        # get_new_faqs = b.elements_xpath(center_col, '//*[starts-with(@class,"related-question-pair")]', 'faqs')
        get_new_faqs = b.afew(elements=center_col,
                              selector='.related-question-pair', bytype='css', try_only=True)
        # get_new_faqs = center_col.find_elements_by_css_selector('.related-question-pair')

        for item in get_new_faqs:
            try:
                item.click()
                print('faqs')
                time.sleep(2)

            except:
                print("Element is not clickable")
        # get_new_faqs2 = center_col.find_elements_by_css_selector(
        get_new_faqs2 = b.afew(elements=center_col,
                               selector='.related-question-pair', bytype='css', try_only=True)
        count = len(get_new_faqs2)
        for item in reversed(list(get_new_faqs2)):
            try:
                count = count-1
                if (len(get_new_faqs)+1) > count:
                    break
                print('faqs2')
                print(count)
                item.click()
                time.sleep(2)

            except:
                print("Element is not clickable")

        time.sleep(5)
        faqs = b.afew(elements=center_col,
                      selector='.related-question-pair', bytype='css')
        len(faqs)
        related_question = []

        for item in faqs:

            print('faqs item')

            # description
            try:
                description = b.one(elements=item,
                                    selector='[data-attrid="wa:/description"]', bytype='css', try_only=True)
                # description = item.find_element_by_css_selector('[data-attrid="wa:/description"]')
                description = description.get_attribute('innerHTML')
            except:
                description = 'no description'

            # link = b.element_xpath(
            #     item, '//*[starts-with(@href,"http")]', 'link')
            try:
                link = b.one(elements=item,
                             selector='a: not([href *= "google.com/search"])', bytype='css', try_only=True)
                link = link.get_attribute('href')
            except:
                link = 'no link'
            try:
                faq = b.one(elements=item,
                            selector='div[id^="exacc_"]', bytype='css', try_only=True)
                faq = faq.text
            except:
                faq = 'not faq'

            question = {
                'ans': re.sub('<[^<]+?>', '', description),
                'link': link,
                'question': re.sub('<[^<]+?>', '', faq)
            }

            related_question.append(question)

        # print('related_question')
        # print(related_question)
        print("related_question")
        print(len(related_question))
        worker_acc.save_data(account_data, worker_token, {"parent_id": worker_keyword['id'],
                                                          "keywords": related_keywords, "question": related_question})

        print('post done')
        print('browser close')
        b.ipinfo_save(software_name='housing')

        print('start :', starttime)
        print('end :', datetime.now().strftime("%H:%M:%S"))
        time.sleep(20)


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
