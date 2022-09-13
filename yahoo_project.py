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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import os
from selenium.webdriver.support.select import Select
from number1 import number
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

        b.get_url('https://login.yahoo.com/')
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
    try:
        create_account = b.driver.find_element(By.XPATH,("//p[@class='sign-up-link']//a"))
        create_account.click()
        time.sleep(2)
        first_name = b.driver.find_element(By.XPATH,("//input[@id='usernamereg-firstName']"))
        first_name.send_keys(account_data['email'])
        first_name = account_data['email']
        print(first_name)

        time.sleep(2)
        last_name = b.driver.find_element(By.XPATH,("//div[@class='last-name pure-u-1-2']//input[@id='usernamereg-lastName']"))
        last_name.send_keys(account_data['password'])
        last_name = account_data['password']
        print(last_name)

        time.sleep(2)
        email_name = b.driver.find_element(By.XPATH,("//input[@name='userId']"))
        email_name.send_keys("ddddf55")
        time.sleep(2)
        suggest_email_name = b.driver.find_elements(By.XPATH,("//ul[@class='desktop-suggestion-list']//li"))[-1]
        values = suggest_email_name.get_attribute('data-value')
        print("Mail_name:",values)
        suggest_email_name.click()


        time.sleep(2)
        email_pass = b.driver.find_element(By.XPATH,("//input[@id='usernamereg-password']"))
        pwd = ran_password()
        print("password:",pwd)
        email_pass.send_keys(pwd)


        #birth_year
        time.sleep(2)
        bd_year = b.driver.find_element(By.XPATH,("//input[@id='usernamereg-birthYear']"))
        bd_year.send_keys("1995")

        next_click = b.driver.find_element(By.XPATH,("//button[@id='reg-submit-button']"))
        next_click.click()

        time.sleep(2)
        pva = number('eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjY0MzYwOTEsImlhdCI6MTYzNDkwMDA5MSwicmF5IjoiY2MzNzRmNTM3MTUyMDc3MWZjODAyNWM1MTM5OWIzYWUiLCJzdWIiOjIzMTAyOH0.OOd17iPERjvtNLc6KNa15nnG5hKXvkzeBf7aJa0ApMjWoO9on4NMC4UIbJRgJ8CtVk2dk7mVi5JwzC1e_zZXis-M2sx1GsFRgWum7BIlyxhYWYYp2rAJuW7YrcAn5MWBXC7E2DaKeeVonDgwzN1_FlUAEnS1iggGgdeKtTy3YZ75mH1z3lrsjjbml_vvP2PrCdpjEl7x2EXBizng3NNxqG72rF9OwI8I5mJj1ks0oHbdMNqOdScdExG6a9MJj9NXOFQmBx9C9bTgCCkhcd1T5bmX5-royaHq8LEyZnuE9HXMwo3mHL_Nny3mwCwftC95dMUqNARrQkY5p0hK4OUQfg','mexico','any','yahoo')

        buy_number = pva.buy_number()
        country_code = pva.country_c
        print(buy_number)

        time.sleep(2)
        country_list = b.driver.find_element(By.XPATH,("//select[@name='shortCountryCode']"))
        optionss =  country_list.find_element(By.XPATH,"//option[@data-code='{0}']".format(country_code))
        optionss.click()

        time.sleep(2)
        country_number = b.driver.find_element(By.XPATH,("//input[@id='usernamereg-phone']"))
        country_number.send_keys('{0}'.format(buy_number)) 

        send_code = b.driver.find_element(By.XPATH,("//button[@name='signup']"))
        send_code.click()

        time.sleep(2)
        code_field = b.driver.find_element(By.XPATH,("//input[@id='verification-code-field']"))
        if code_field:
            check_sms = pva.check_sms()
            print(check_sms)
            code_field.send_keys('{0}'.format(check_sms))

            time.sleep(2)
            next = b.driver.find_element(By.XPATH,("//button[@name='verifyCode']"))
            next.click()

            time.sleep(2)
            next = b.driver.find_element(By.XPATH,("//button[@type='submit']"))
            next.click()

        # text_file_write
        f = open("yaaho.txt", "a")
        f.write("{0}:{1}:{2}:{3}\n".format(first_name,last_name,values,pwd))
        f.close()
        #open and read the file after the appending:
        f = open("yaaho.txt", "r")
        print(f.read())
    except:
        pass


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