
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
        create_account = b.visibil_element('xpath',"//p[@class='sign-up-link']//a")
        create_account.click()
        time.sleep(5)
        
        first_name = b.visibil_element('xpath',"//input[@id='usernamereg-firstName']")
        for character in name[0].replace('\n',''):
            print(character)
            time.sleep(0.2)
            first_name.send_keys(character)
        print(name[0])

        time.sleep(5)
        last_name = b.visibil_element('xpath',"//div[@class='last-name pure-u-1-2']//input[@id='usernamereg-lastName']")
        for character in name[1].replace('\n',''):
            print(character)
            time.sleep(0.2)
            last_name.send_keys(character)
        print(name[1])

        time.sleep(5)
        email_name = b.visibil_element('xpath',"//input[@name='userId']")
        fullname = name[0]+name[1]
        for character in fullname.replace('\n',''):
            print(character)
            time.sleep(1)
            email_name.send_keys(character)
            suggest_email_name = b.visibil_element('xpath',"//ul[@class='desktop-suggestion-list']//li")
            if suggest_email_name:
                values = suggest_email_name.get_attribute('data-value')
                print("Mail_name:",values)
                suggest_email_name.click()
                break
        time.sleep(5)
        # suggest_email_name = b.visibil_element('xpath',"//ul[@class='desktop-suggestion-list']//li")
        # if suggest_email_name:
        #     values = suggest_email_name.get_attribute('data-value')
        #     print("Mail_name:",values)
        #     suggest_email_name.click()
        # else:
        #     print('Not suggest username')
            


        time.sleep(5)
        email_pass = b.visibil_element('xpath',"//input[@id='usernamereg-password']")
        pwd = ran_password()
        print("password:",pwd)
        email_pass.send_keys(pwd)


        #birth_year
        time.sleep(5)
        bd_year = b.visibil_element('xpath',"//input[@id='usernamereg-birthYear']")
        bd_year.send_keys("1995")

        next_click = b.visibil_element('xpath',"//button[@id='reg-submit-button']")
        next_click.click()

        time.sleep(5)
        buy_number = pva.buy_number()
        country_code = pva.country_c
        print(buy_number)

        print('wait for CountryCode')
        # time.sleep(500)
        # return False
        
        
        country_list = b.driver.find_element(By.XPATH,"//select[@name='shortCountryCode']")
        optionss =  country_list.find_element(By.XPATH,"//option[@data-code='{0}']".format(country_code))
        optionss.click()

        time.sleep(5)
        country_number = b.visibil_element('xpath',"//input[@id='usernamereg-phone']")
        country_number.send_keys('{0}'.format(buy_number)) 

        send_code = b.visibil_element('xpath',"//button[@name='signup']")
        send_code.click()

        
        
        recaptcha =b.visibil_element('xpath',"//iframe[@id='recaptcha-iframe']")
        if recaptcha:
            time.sleep(200)
            
            
            chacha_worker = capcha('73644003524468b0603694eff6fb6e6f','4191a9a8a00ad6ce300a49d8d36935da')




            site_url = b.current_url()

            chacha_key = chacha_worker.two_captcha('6Ldbp6saAAAAAAwuhsFeAysZKjR319pRcKUitPUO', site_url,enterprise=1)

            chacha_respons = b.driver.find_element_by_id('g-recaptcha-response')
            print('g-recaptcha-response')
            b.script_run("document.getElementById('g-recaptcha-response').style.display = 'block';")
            print('g-recaptcha-response block')
            script = 'document.getElementById("g-recaptcha-response").innerHTML="{}";'.format(chacha_key)
            
            b.script_run(script)
            print('g-recaptcha-response set data')
            b.script_run("document.getElementById('g-recaptcha-response').style.display = 'none';")
            print('g-recaptcha-response none')
            submit1 =b.select_element('[id="recaptcha-submit"]')
            submit1.click()
        
        code_field = b.visibil_element('xpath',"//input[@id='verification-code-field']")
        if code_field:
            check_sms = pva.check_sms()
            print(check_sms)
            code_field.send_keys('{0}'.format(check_sms))

            time.sleep(2)
            next = b.visibil_element('xpath',"//button[@name='verifyCode']")
            next.click()

            time.sleep(2)
            next = b.visibil_element('xpath',"//button[@type='submit']")
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