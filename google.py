
import time
import shutil
import random
import sys
from os import path
from pyvirtualdisplay import Display
from datetime import datetime
from ps_lib.browser import browser
from ps_lib.accounts import accounts
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import os
# import pyautogui
import re

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))

def checkTimeOut(starttime,workerTimeOut=5):

    fmt = '%Y-%m-%d %H:%M:%S'
    now = datetime.now()
    d1 = datetime.strptime(starttime.strftime(fmt), fmt)
    d2 = datetime.strptime(now.strftime(fmt), fmt)


    # Convert to Unix timestamp
    d1_ts = time.mktime(d1.timetuple())
    d2_ts = time.mktime(d2.timetuple())
    d1_ts = time.mktime(d1.timetuple())

    # They are now in seconds, subtract and then divide by 60 to get minutes.
    ruinngtime= d2_ts-d1_ts
    print('software runing in ',ruinngtime)
    workerTimeOut=workerTimeOut*60
    if workerTimeOut<ruinngtime:
        return True













def scrolling(b):
    total_height = int(b.driver.execute_script(
    "return document.body.scrollHeight"))


    total = total_height / random.choice([2, 3, 4, 7, 1])


    for i in range(1, round(total), 1):
        time.sleep(0.02)
        b.driver.execute_script("window.scrollTo(0, {});".format(i))
def nextclick(b,tragetdomain):


    target_site_link = b.finds("//div[@class='single-content2']//a[contains(@href,'https://{}')]".format(tragetdomain),'intarnal links')
    randon_link = random.choice(target_site_link)
    b.driver.get(randon_link.get_attribute('href'))
    # randon_link.click()
starttime = datetime.now()
def target_site(b,tragetdomain):
    if checkTimeOut(starttime,workerTimeOut):
        return True
    if random.choice([2,3,1]) ==1:
        scrolling(b)
        nextclick(b,tragetdomain)
        target_site(b,tragetdomain)
    if random.choice([2,3,1]) ==2:

        nextclick(b,tragetdomain)
        scrolling(b)
        target_site(b,tragetdomain)
    if random.choice([2,3,1]) ==3:

        nextclick(b,tragetdomain)
        scrolling(b)

        # comment_text_area = b.find("//div[@class='comment-form wow fadeIn animated']//textarea",'coment_area','xpath')
        # comment_text_area.send_keys("Hi! I am new in here.")

        # comment_text_area_name = b.find("//div[@class='comment-form wow fadeIn animated']//input[@name='name']")
        # comment_text_area_name.send_keys("SM Samrat")

        # comment_text_area_email = b.find("//div[@class='comment-form wow fadeIn animated']//input[@name='email']")

        # comment_text_area_email.send_keys("SM@gmail.com")

        # comment_text_area_website = b.find("//div[@class='comment-form wow fadeIn animated']//input[@name='website']")
        # comment_text_area_website.send_keys("samrat.com")

        # comment_text_area_post_comment = b.find("//div[@class='comment-form wow fadeIn animated']//button")
        # comment_text_area_post_comment.click()

        target_site(b,tragetdomain)

    time.sleep(2)
    return True
workerTimeOut =random.choice([3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20])
def main(account_data, postinfo, packages_id, body_mail):
    # work start time
    global starttime

    starttime = datetime.now()
    print(account_data)
    postinfo = postinfo.get_post(account_data['id'])

    print(postinfo)



    print(datetime.now().strftime("%H:%M:%S"))

    account_id = account_data['id']
    print("account id: ", account_id)
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

    try:

        b.get_url('https://www.google.com')
    except:
        b.exit()
    # time.sleep(240)
    google = b.find("//input[@class='gLFyf gsfi']",'google link')
    # time.sleep(150)
    google.send_keys(account_data['email'])
    google.send_keys(Keys.ENTER)
    avarage_position = int(account_data['post_data'] +str(50))
    page = round((avarage_position)/10,2)
    runing_page = 0
    while True:
        target_link= False
        target_link = b.find("//a[contains(@href,'https://{}')]".format(account_data['password']),'traget link',try_only=True)
            # time.sleep(150)
        if target_link:

            target_link.click()
            time.sleep(5)
            target_site(b,account_data['password'])
            b.exit()
            break


        else:
            print('next page : ',runing_page)
            runing_page =runing_page+1
            if runing_page>page:
                break
            next_page_link = b.find('//*[@id="pnnext"]','google next page','xpath')
            if next_page_link:
                next_page_link.click()
            
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