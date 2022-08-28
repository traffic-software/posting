
import time
import shutil
import random
import sys
from os import path
from pynput.keyboard import Key, Controller
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

keyboard = Controller()
def topScroling(countTop):
    for i in range(1, countTop, 1):
        
        print('press up key')
        keyboard.press(Key.up)
        keyboard.release(Key.up)
    
def downScroling(countTop):
    for i in range(1, countTop, 1):
        
        print('press down key')
        keyboard.press(Key.down)
        keyboard.release(Key.down)
    
def scrolling(b):
    total_height = int(b.driver.execute_script(
    "return document.body.scrollHeight"))
    


    total = total_height / random.choice([2, 3, 4, 7, 1.2])
    


    for i in range(1, round(total), 80):
    
        scrollBar = int(b.driver.execute_script("return window.scrollY"))
        print(total_height)
        print(scrollBar)
        time.sleep(random.choice([3,4,5,6,10,8]))
        if scrollBar < round(total):
            if random.choice([20,21,23,22, 3, 4, 5,6,10,8,15,13,12,17])<22:
                
                downScroling(random.choice([20,21,23,22, 3, 4, 5,6,10,8,15,13,12,17]))
            
            
            else:
                topScroling(random.choice([2, 3, 4, 5,6]))
                if random.choice([2, 3, 4, 5,6])==2:
                    break
        else:
            break
                
            
            
            
            
        # b.driver.execute_script("window.scrollTo(0, {});".format(i))
        # mouse.scroll(0, total)
def nextclick(b,parent):


    linkselector = "{0}//a[contains(@href,'https://')]".format(parent)
    print(linkselector)
    target_site_link = b.finds(linkselector,'intarnal links')
    randon_link = random.choice(target_site_link)
    b.driver.get(randon_link.get_attribute('href'))
    return True
starttime = datetime.now()
def target_site(b,parent):
    print('target_site')
    worker_conditon=random.choice([2,3,1])
    if checkTimeOut(starttime,workerTimeOut):
        return True
    if worker_conditon ==1:
        scrolling(b)
        nextclick(b,parent)
        target_site(b,parent)
    if worker_conditon ==2:

        nextclick(b,parent)
        scrolling(b)
        target_site(b,parent)
    if worker_conditon ==3:

        nextclick(b,parent)
        scrolling(b)

        target_site(b,parent)

    time.sleep(2)
    return True
workerTimeOut =random.choice([3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20])
def main(account_data, postinfo, packages_id, body_mail):
    # work start time
    global starttime

    message=""
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

        b.get_url('https://'+account_data['email'])
    except:
        b.exit()
    
    worker_acc.ban_3(account_data['id'])
    
    target_site(b,account_data['post_data'])
    b.exit()
    worker_acc.post_done(account_data['id'],account_data['email'])
            
    print('post done')
    print('browser close')
    b.ipinfo_save(software_name='CoreAiSite-'+str(workerTimeOut)+'M'+message)

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