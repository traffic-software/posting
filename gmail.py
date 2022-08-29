import time
import shutil
import random
import sys
import os
from os import path
import re
from pyvirtualdisplay import Display
from datetime import datetime

from ps_lib.browser import browser
from ps_lib.accounts import accounts
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from ps_lib.uc import ucbrowser
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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


    # b = browser(account_id, pva=account_data)
    b = ucbrowser(account_id, pva=account_data)


    time.sleep(5)
    # if b.PROXY_PASS == False:
    #     b.exit()
    #     print('proxy condition not fulfilled')
    #     # worker_acc.ban_3(account_id, 5)
    #     time.sleep(10)
    #     return False

    #start your work
    try:

        b.get_url('https://accounts.google.com/signin/v2/identifier?continue=https%3A%2F%2Fmyaccount.google.com%2Fsigninoptions%2Frescuephone&osid=1&rart=ANgoxcfbj5MICImsby3i6E4WliB4NiCObSuRKGTYLSt03bQVr5EN0ekxnuxLrRGkyz5DKW13ZqMxZkUoZn1oMKAXz3u6m-8mXw&service=accountsettings&flowName=GlifWebSignIn&flowEntry=ServiceLogin')
    except:
        b.exit()

    def ran_password():
        characters ="abcdefghijklmnopshwyz"
        upper ="ABCDEFGHIJKLMNOPQPSHWYZ"
        symbol ="@%"
        num = "0123456789"
        string = characters+symbol+num+upper
        length = 8
        password = "".join(random.sample(string,length))
        print("Random password:",password)
        return password
    

    time.sleep(2)
    Enter_gmail = b.driver.find_element(By.XPATH,("//input[@type='email']"))
    Enter_gmail.send_keys(account_data['email'])
    next = b.driver.find_elements(By.XPATH,("//span[@class='VfPpkd-vQzf8d']"))[1]
    next.click()
    time.sleep(3)
    password=False
    try:
        password = b.driver.find_element(By.XPATH,("//input[@type='password']"))
        password.send_keys(account_data['password'])
        next = b.driver.find_elements(By.XPATH,("//span[@class='VfPpkd-vQzf8d']"))[1]
        next.click()

        time.sleep(2)


        if "challenge/selection" in b.current_url():

            click_rec_mail_link = b.driver.find_elements(By.XPATH,("//div[@class='vxx8jf']"))[2]
            click_rec_mail_link.click()
            time.sleep(2)
            enter_rec_mail = b.driver.find_element(By.XPATH,("//input[@type='email']"))
            enter_rec_mail.send_keys(account_data['extra'])
            next = b.driver.find_element(By.XPATH,("//button[@class='VfPpkd-LgbsSe VfPpkd-LgbsSe-OWXEXe-k8QpJ VfPpkd-LgbsSe-OWXEXe-dgl2Hf nCP5yc AjY5Oe DuMIQc LQeN7 qIypjc TrZEUc lw1w4b']//span[@class='VfPpkd-vQzf8d']"))
            next.click()

        time.sleep(2)
        link = b.current_url()
        linkarg=link.split('?')
        b.get_url("https://myaccount.google.com/signinoptions/password?"+linkarg[1])

        # password = b.driver.find_element(By.XPATH,("//input[@type='password']"))
        # password.send_keys(account_data['password'])
        # next = b.driver.find_elements(By.XPATH,("//span[@class='VfPpkd-vQzf8d']"))[1]
        # next.click()
        time.sleep(2)
        
        password = b.driver.find_element(By.XPATH,("//input[@name='password']"))
        pwd = ran_password()
        password.send_keys(pwd)
        cm_password = b.driver.find_element(By.XPATH,("//input[@name='confirmation_password']"))
        cm_password.send_keys(pwd)
        change_password = b.driver.find_element(By.XPATH,("//span[@class='VfPpkd-vQzf8d']"))
        change_password.click()

        
        
        update_rec=account_data['extra']
        if '@' in account_data['post_data']:
            print('in recovary mail chenge')
            link=b.current_url()
            linkarg = link.split('?')
            b.get_url("https://myaccount.google.com/recovery/email?"+linkarg[1])
            time.sleep(5)

            rec_mail = b.driver.find_element(By.XPATH,("//input[@class='VfPpkd-fmcmS-wGMbrd CtvUB']"))
            rec_mail.clear()
            rec_mail.send_keys(account_data['post_data'])
            rec_next = b.driver.find_element(By.XPATH,("//button[@class='VfPpkd-LgbsSe VfPpkd-LgbsSe-OWXEXe-k8QpJ VfPpkd-LgbsSe-OWXEXe-dgl2Hf nCP5yc AjY5Oe DuMIQc LQeN7 SdOXCb']"))
            rec_next.send_keys(Keys.ENTER)
            update_rec=account_data['post_data']
        

        # Open a file with access mode 'a'
        file_object = open('sample.txt', 'a')
        # Append 'hello' at the end of file
        file_object.write('{0}:{1}:{2}\n'.format(account_data['email'],pwd,update_rec))
        # Close the file
        file_object.close()
    except:
        password=False
        worker_acc.ban_3(account_data['id'])





    print('browser close')
    worker_acc.ban_3(account_data['id'])
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