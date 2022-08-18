from email.policy import SMTP
from re import I, sub
import threading
import time
import shutil
import random
import string
import fnmatch
import subprocess
import sys
from os import path
from zipfile import error
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

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))

# from pynput.mouse import Button, Controller


def main(account_data, postinfo, packages_id, body_mail):
    # work start time
    starttime = datetime.now().strftime("%H:%M:%S")

    print(datetime.now().strftime("%H:%M:%S"))
    # print(account_data)
    account_id = account_data['id']
    worker_acc = accounts()
    use_proxy = True

    b = browser(account_id, pva=account_data)

    time.sleep(5)
    if b.PROXY_PASS == False and b.use_proxy == True:
        b.exit()
        print('proxy condition not fulfilled')
        # worker_acc.ban_3(account_id, 5)
        time.sleep(10)
        return False

    try:
        b.get_url(account_data['email'])
    except:
        b.exit()

    if b.try_xpath("//*[contains(text(),'posting has been flagged')]"):
        print('This posting has been flagged for removal')
        worker_acc.ban_3(account_id, status=3)
    else:

        hidenbutton = b.select_element_xpath(
            '//*[@class="banish-unbanish action"]', 'hiden try')

        hidenbutton.click()
        flagbutton = b.select_element_xpath(
            '//*[@class="flag-action action"]', 'flaging try')

        flagbutton.click()

        worker_acc.post_error(
            account_id, "flag action try", software_type='clf')
        #title="thanks for flagging!"
        b.wait('//*[@title="thanks for flagging!"]')
        time.sleep(2)

    b.ipinfo_save(software_name='clf')

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
    time.sleep(10)
