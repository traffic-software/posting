import time
import shutil
import sys
from os import path
from pyvirtualdisplay import Display
from datetime import datetime
from ps_lib.firefox import firefoxBrowser
from ps_lib.browser import browser
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
    # b = firefoxBrowser(account_id, pva=account_data)

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

    for no in range(int(account_data['extra']), int(account_data['extra'])+10000):
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
            worker_acc.update_account(data=no, id=account_data['id'])
            b.get_url(loginurl)
        if 'signinrejecte' in b.current_url():
            print('rejected')
            oldNumber = no-1
            worker_acc.save_account(
                data=oldNumber, soft_token=account_data['password'])
            print(oldNumber)

            b.get_url(loginurl)
        if 'challenge/pwd' in b.current_url():
            # print('password')
            if b.try_select_element('[name="password"]'):
                time.sleep(20)
                print('passwdord area')

                b.select_element('[name="password"]').send_keys(no)

        imgcapch = b.try_select_element('[id="captchaimg"]')

        try:

            if imgcapch.get_attribute('src'):
                b.get_url(loginurl)
                # print('imgcapch')
                continue
        except:
            b.get_url(loginurl)
            continue

        if 'identifier' in b.current_url():
            # print('identifier')

            try:
                b.wait_css('[id="identifierId"]')
                number = b.select_element('[id="identifierId"]')
                number.clear()
                number.send_keys(0)
                number.send_keys(no)
            except:
                b.get_url(loginurl)
                continue

        nextpage = b.try_select_element(
            '#identifierNext button[type="button"]')
        try:
            nextpage.click()
        except:
            continue

    b.ipinfo_save(software_name='gmail creator')

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
