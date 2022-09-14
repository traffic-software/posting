# from pynput.mouse import Button, Controller
from turtle import back
from pynput.keyboard import Key, Controller
import time
import random
import shutil
import sys
from os import path
from pyvirtualdisplay import Display
from datetime import datetime
from ps_lib.firefox import firefoxBrowser
from ps_lib.browser import browser
from ps_lib.uc import ucbrowser
from ps_lib.accounts import accounts
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.ps_str import ps_str
from ps_lib.imap import imap
from selenium.webdriver.common.keys import Keys
import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))
os.path.dirname(os.path.abspath(__file__))

keyboard = Controller()
# keyboard.type(str(258956856))


def main():
    # work start time
    starttime = datetime.now().strftime("%H:%M:%S")

    print(datetime.now().strftime("%H:%M:%S"))
    # print(account_data)
    

    # b = browser(account_id, pva=account_data)
    # b = firefoxBrowser(account_id, pva=account_data)
    b = ucbrowser()

    time.sleep(1)

    try:
        loginurl = 'https://accounts.google.com/signin/v2/identifier'

        b.get_url(loginurl)
        # b.get_url('https://accounts.google.com/signup/v2/webcreateaccount?service=mail&biz=false&flowName=GlifWebSignIn&flowEntry=SignUp')
    except:
        b.exit()
    # time.sleep(120)
    count = 0
    # list to store file lines
    lines = []
    # read file
    with open(r"input.txt", 'r') as fp:
        # read an store all lines into list
        lines = fp.readlines()

    # Write file
    with open(r"input.txt", 'w') as fp:
        # iterate each line
        for number, line in enumerate(lines):
            # delete line 5 and 8. or pass any Nth line you want to remove
            # note list index starts from 0
            if number != 0:
                fp.write(line)

    for no in range(0, 20):
        time.sleep(1)

        # rejeted
        # https://accounts.google.com/signin/v2/deniedsigninrejected
        # login page
        loginurl = 'https://accounts.google.com/signin/v2/identifier'
        # password page
        # https://accounts.google.com/signin/v2/challenge/pwd
        count = count+1
        
        if count % 20 == 1:
            
            b.get_url(loginurl)
        if 'signinrejecte' in b.current_url():

            b.get_url(loginurl)

        if 'challenge/pwd' in b.current_url():
            password = b.visibil_element('name', "password")

            mailpass = lines[1]
            password.clear()
            password.send_keys(mailpass)

            passwordNext = b.visibil_element(
                'css', '[id="passwordNext"] [type="button"]')
            passwordNext.click()
            print(mailpass)
            time.sleep(5)
            if b.visibil_element('name', "password", wait=10):
                # print('pssword not match')
                b.get_url(loginurl)
                continue
            else:
                print('pssword matched')

        try:
            imgcapch = b.visibil_element('id', "captchaimg", wait=1)

            if imgcapch.get_attribute('src'):
                # print('imgcapch')

                b.get_url(loginurl)

                continue
        except:
            pass
            # print('except imgcapch')
            # time.sleep(60)
            # b.get_url(loginurl)
            # continue

        if 'identifier' in b.current_url():
            # print('identifier')

            # time.sleep(60)
            try:

                number = b.visibil_element('name', "identifier")
                number.clear()

                number.send_keys(lines[0])
            except:
                b.get_url(loginurl)
                continue

        nextpage = b.visibil_element(
            'css', '#identifierNext button[type="button"]', wait=1)
        try:
            nextpage.click()
        except:
            continue

    b.ipinfo_save(software_name='gmail password')

    b.exit()
    print('browser close')

    print('start :', starttime)
    print('end :', datetime.now().strftime("%H:%M:%S"))





# print(acc.get_proxy_list())
# exit()

# x = threading.Thread(target=smtp.reply_check, args=(1,), daemon=True)
# x.start()
while True:

    print('start new')
    main()
    time.sleep(1)
