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
from ps_lib.browser import browser
from ps_lib.uc import ucbrowser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.ps_str import ps_str
from ps_lib.imap import imap
import os

from selenium.webdriver.support.select import Select
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

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
    # b = ucbrowser(account_id, pva=account_data)
    chacha_worker = capcha('73644003524468b0603694eff6fb6e6f','4191a9a8a00ad6ce300a49d8d36935da',2)
    cProxy=b.PROXY_USER+':'+b.PROXY_PASS+'@'+b.PROXY_HOST+':'+b.PROXY_PORT
    cProxyType=b.PROXY_TYPE
    if b.PROXY_TYPE == "PROXY":
        cProxyType ='http'
        
        
    cid = chacha_worker.two_start('B7D8911C-5CC8-A9A3-35B0-554ACEE604DA', 'https://signup.live.com/?lic=1  ','https://client-api.arkoselabs.com',cProxy,cProxyType)




	


    time.sleep(5)
    # if b.PROXY_PASS == False:
    #     b.exit()
    #     print('proxy condition not fulfilled')
    #     # worker_acc.ban_3(account_id, 5)
    #     time.sleep(10)
    #     return False

    #start your work
    try:

        b.get_url('https://signup.live.com/?lic=1')
    except:
        b.exit()
    create_new_hotmail=False
    try:
        create_new_hotmail = b.driver.find_element(By.XPATH,("//div[@class='form-group-last-child']//a"))
        create_new_hotmail.click()
        time.sleep(2)

        option = b.driver.find_element(By.XPATH,("//option[@value='hotmail.com']"))
        option.click()

        time.sleep(3)
        input_hotmail_text = b.driver.find_element(By.XPATH,("//div[@class='row']//input"))
        input_hotmail_text.send_keys("nnewc2k_rer45er2")

        next_button = b.driver.find_element(By.XPATH,("//div[@class='inline-block']//input[@type='submit']"))
        next_button.click()

        time.sleep(5)
        password_input = b.driver.find_element(By.XPATH,("//input[@type='password']"))
        password_input.send_keys("w23#5!EWs3456t")
        next_button = b.driver.find_element(By.XPATH,("//div[@class='inline-block']//input[@type='submit']"))
        next_button.click()

        time.sleep(2)

        first_name = b.driver.find_element(By.XPATH,("//div[@class='row']//input[@id='FirstName']"))
        first_name.send_keys("jakir")

        last_name = b.driver.find_element(By.XPATH,("//div[@class='row']//input[@id='LastName']"))
        last_name.send_keys("hossen")

        next_button = b.driver.find_element(By.XPATH,("//div[@class='inline-block']//input[@type='submit']"))
        next_button.click()

        #birth_month
        time.sleep(3)
        month = b.driver.find_element(By.ID,"BirthMonth")
        mdb = Select(month)
        mdb.select_by_visible_text('April')

        #birth_day
        time.sleep(2)
        day = b.driver.find_element(By.ID,"BirthDay")
        bday=Select(day)
        bday.select_by_visible_text('6')


        #birth_year
        time.sleep(2)
        bd_year = b.driver.find_element(By.XPATH,("//input[@type='number']"))
        bd_year.send_keys("1997")
        next_button = b.driver.find_element(By.XPATH,("//div[@class='inline-block']//input[@type='submit']"))
        next_button.click()
        
        # time.sleep(50)
        frame=b.visibil_element('id',"enforcementFrame",60)
        b.iframe(frame)
        token=b.driver.find_element(By.XPATH,("//input[@id='verification-token']"))
        
        tokeninfo = token.get_attribute('value')
        pipe_line = tokeninfo.split('|')
        pk = pipe_line[10]
        pure_pk = pk[3:]

        surl = pipe_line[15]
        pure_surl = surl[5:]
        
        # responsekey = chacha_worker.two_captcha(pure_pk, b.current_url(),pure_surl,cProxy,cProxyType)
        # print(responsekey['key'])
        token=b.driver.find_element(By.XPATH,("//input[@id='FunCaptcha-Token']"))
        # b.script_run("document.getElementById('FunCaptcha-Token').value = '{0}';".format(responsekey['key']))
        b.script_run("document.getElementById('FunCaptcha-Token').value = '{0}';".format(chacha_worker.two_respond(cid)))

        #nested multiple iframe convert
        # frames = b.driver.find_element(By.ID,'enforcementFrame')
        # b.iframe(frames)
        # time.sleep(5)
        # frame1 = b.driver.find_element(By.XPATH,"//iframe[@id='fc-iframe-wrap']")
        # b.iframe(frame1)
        # time.sleep(5)
        # frame2 = b.driver.find_element(By.XPATH,"//iframe[@id='CaptchaFrame']")
        # b.iframe(frame2)
        # time.sleep(2)
        # next_button = b.driver.find_element(By.XPATH,("//button[@id='home_children_button']"))
        # next_button = b.driver.find_element(By.XPATH,("//button[@id='home_children_button']"))

        # next_button.click()
        b.switch_back()
        form = b.driver.find_element(By.XPATH,("//form[@id='HipEnforcementForm']"))
        form.submit()
        print('submet')
        time.sleep(2000)
        # b.switch_back()
    except:
        create_new_hotmail=False




    print('browser close')
    b.ipinfo_save(software_name='hotmail')

    # print('start :', starttime)
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