
import requests
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
from datetime import date
d1 =str(date(2022,9,15))
d2 =str(date.today())


def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y-%m-%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return abs((d2 - d1).days)
if days_between(d1, d2) >= 90:
    print("""
              wellcome to pointssoft.com 
              new update available
              """)
    time.sleep(60)
    exit()
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))
import requests
def get_prices(product):

    headers = {
        'Accept': 'application/json',
    }

    params = (
        ('product', product),
    )
    response = requests.get('https://5sim.net/v1/guest/prices', headers=headers, params=params)
    items = response.json()[product]
    for i in items:
        
        price=0
        count=0
        fastitem={}
        avarage=0
        for n in items[i].values():
            # print(n)
            price +=n['cost']
            count +=n['count']
            avarage +=1
       
        fastitem['country']=i
        fastitem['avarage ']=price/avarage
        fastitem['count']=count
        if fastitem['avarage '] <= 12:
            print(fastitem)
            print('.............................')

get_prices('yahoo')
f = open("5sim.txt", "r")
country=input('plz input contry name:')
pva = number(f.read(),country,'any','yahoo')

def ran_password():
        characters ="abcdefghijklmnopshwyz"
        upper ="ABCDEFGHIJKLMNOPQPSHWYZ"
        symbol ="@%^&*()"
        num = "0123456789"
        string = characters+symbol+num+upper
        length = 12
        password = "".join(random.sample(string,length))
        print("Random password:",password)
        return password
def main():
    # work start time


    starttime = datetime.now()




    print(datetime.now().strftime("%H:%M:%S"))


    # b = browser(account_id, pva=account_data)
    b = ucbrowser()
    try:
        # list to store file lines
        lines = []
        # read file
        with open(r"input.txt", 'r') as fp:
            # read an store all lines into list
            lines = fp.readlines()

        # Write file
        with open(r"input.txt", 'w') as fp:
            for number, line in enumerate(lines):
                if number != 0:
                    fp.write(line)
        name=lines[0].split(':')
    except:
        b.exit()
        print('account format or other problem')
        time.sleep(20)
        return False


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

    
    try:
        create_account = b.driver.find_element(By.XPATH,("//p[@class='sign-up-link']//a"))
        create_account.click()
        time.sleep(2)
        
        first_name = b.driver.find_element(By.XPATH,("//input[@id='usernamereg-firstName']"))
        first_name.send_keys(name[0])
        first_name = name[0]
        print(first_name)

        time.sleep(2)
        last_name = b.driver.find_element(By.XPATH,("//div[@class='last-name pure-u-1-2']//input[@id='usernamereg-lastName']"))
        last_name.send_keys(name[1])
        last_name = name[1]
        print(last_name)

        time.sleep(2)
        email_name = b.driver.find_element(By.XPATH,("//input[@name='userId']"))
        email_name.send_keys(name[0]+name[1])
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
        f = open("output.txt", "a")
        f.write("{0}:{1}".format(values+"@yahoo.com",pwd))
        f.close()
        #open and read the file after the appending:
        f = open("output.txt", "r")
        print(f.read())
    except:
        pass


    print('browser close')

    print('start :', starttime)
    print('end :', datetime.now().strftime("%H:%M:%S"))



while True:
    
    print('start new')
    main()
    time.sleep(1)