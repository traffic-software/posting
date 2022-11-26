# from pynput.mouse import Button, Controller
from logging import exception
from turtle import back
from pynput.keyboard import Key, Controller
import time
import random
import shutil
import sys
from datetime import date


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
from selenium.webdriver.common.by import By
import os
from datetime import date
d1 = str(date(2022, 9, 15))
d2 = str(date.today())
date.day


def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y-%m-%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return abs((d2 - d1).days)


# if days_between(d1, d2) >= 60:
#     print("""
#               wellcome to pointssoft.com
#               new update available
#               """)
#     time.sleep(60)
#     exit()
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))
os.path.dirname(os.path.abspath(__file__))

keyboard = Controller()
# keyboard.type(str(258956856))


def ran_password():
    characters = "abcdefghijklmnopshwyzABCDEFGHIJKLMNOPQSTUVWXYZ"
    upper = "ABCDEFGHIJKLMNOPQPSHWYZ"
    symbol = "@%*^$#"
    num = "0123456789"
    string = characters+symbol+num+upper
    length = 20
    password = "".join(random.sample(string, length))
    print("Random password:", password)
    return password


def main():
    # work start time
    starttime = datetime.now().strftime("%H:%M:%S")

    print(datetime.now().strftime("%H:%M:%S"))
    # print(account_data)

    # b = browser(account_id, pva=account_data)
    # b = firefoxBrowser(account_id, pva=account_data)
    b = ucbrowser(profile_dir='profile')

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
        mailinfo = lines[0].split(':')
    except:
        b.exit()
        print('account format or other problem')
        time.sleep(20)
        return False

    try:

        b.get_url('https://accounts.google.com/signin/v2/challenge/selection')
        b.driver.delete_all_cookies()
        b.get_url('https://accounts.google.com/signin/v2/identifier?continue=https%3A%2F%2Fmyaccount.google.com%2Fsigninoptions%2Frescuephone&osid=1&rart=ANgoxcfbj5MICImsby3i6E4WliB4NiCObSuRKGTYLSt03bQVr5EN0ekxnuxLrRGkyz5DKW13ZqMxZkUoZn1oMKAXz3u6m-8mXw&service=accountsettings&flowName=GlifWebSignIn&flowEntry=ServiceLogin')
    except:

        b.exit()
        return False

    try:
        Enter_gmail = b.driver.find_element(
            By.XPATH, ("//input[@type='email']"))
        print('email typing:', mailinfo[0])
        Enter_gmail.send_keys(mailinfo[0])

        next = b.driver.find_elements(
            By.XPATH, ("//span[@class='VfPpkd-vQzf8d']"))[1]
        next.click()
        time.sleep(10)
        password = False
    except:

        b.exit()
        print('account typing problem')
        time.sleep(20)
        return False
    try:
        # https://accounts.google.com/signin/v2/challenge/selection
        # https://accounts.google.com/signin/v2/challenge/kpe
        password = b.driver.find_element(
            By.XPATH, ("//input[@type='password']"))
        print('old password typing:', mailinfo[1])
        password.send_keys(mailinfo[1])
        next = b.driver.find_elements(
            By.XPATH, ("//span[@class='VfPpkd-vQzf8d']"))[1]
        next.click()

        time.sleep(10)
    except:
        b.exit()
        print('password typing problem')
        time.sleep(20)
        return False
    try:

        if "challenge/selection" in b.current_url():
            # //div[@data-challengetype='12']

            click_rec_mail_link = b.driver.find_element(
                By.XPATH, ("//div[@data-challengetype='12']"))
            click_rec_mail_link.click()
            time.sleep(10)
            enter_rec_mail = b.driver.find_element(
                By.XPATH, ("//input[@type='email']"))
            print('old recovery typing:', mailinfo[2])
            enter_rec_mail.send_keys(mailinfo[2])
            next = b.driver.find_element(
                By.XPATH, ("//button[@class='VfPpkd-LgbsSe VfPpkd-LgbsSe-OWXEXe-k8QpJ VfPpkd-LgbsSe-OWXEXe-dgl2Hf nCP5yc AjY5Oe DuMIQc LQeN7 qIypjc TrZEUc lw1w4b']//span[@class='VfPpkd-vQzf8d']"))
            next.click()
    except:
        # b.exit()
        # print('recovery typing problem')
        # time.sleep(20)
        # return False
        pass

    try:

        print('in recovary mail chenge')
        link = b.current_url()
        linkarg = link.split('?')
        b.get_url("https://myaccount.google.com/recovery/email?"+linkarg[1])
        time.sleep(15)
        rec_mail = b.driver.find_element(
            By.XPATH, ("//input[@class='VfPpkd-fmcmS-wGMbrd CtvUB']"))
        rec_mail.clear()
        rec_mail.send_keys(mailinfo[3])
        rec_mail.send_keys(Keys.ENTER)
        # rec_next = b.driver.find_element(
        #     By.XPATH, "(//form//input[@type='text'])[last()]")
        # rec_next.send_keys(Keys.ENTER)
        update_rec = mailinfo[3]
        time.sleep(15)
    except:
        b.exit()
        print('recovary mail add problem')
        time.sleep(20)
        return False
    try:

        # Open a file with access mode 'a'
        file_object = open('output.txt', 'a')
        # Append 'hello' at the end of file
        file_object.write('{0}:{1}:{2}\n'.format(
            mailinfo[0], mailinfo[1], update_rec))
        # Close the file
        file_object.close()
    except:
        b.exit()
        print('{0}:{1}:{2}\n'.format(mailinfo[0], mailinfo[1], update_rec))
        print('output problem')
        time.sleep(20)
        return False

    # b.ipinfo_save(software_name='gmail password')

    b.exit()
    print('browser close')

    print('start :', starttime)
    print('end :', datetime.now().strftime("%H:%M:%S"))


while True:

    print('start new')
    main()
    time.sleep(1)
