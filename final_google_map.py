
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

from selenium.webdriver.support.select import Select
import json
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


    b = browser(account_id, pva=account_data)


    time.sleep(5)
    # if b.PROXY_PASS == False:
    #     b.exit()
    #     print('proxy condition not fulfilled')
    #     # worker_acc.ban_3(account_id, 5)
    #     time.sleep(10)
    #     return False

    #start your work
    try:

        b.get_url('https://www.google.com/maps')
    except:
        b.exit()

    def waits(driver,x):

        try:
            wait = WebDriverWait(driver, 30)
            return wait.until(EC.presence_of_all_elements_located((By.XPATH, x)))
        except:
            return False

    def wait(driver,x):

        try:
            wait = WebDriverWait(driver, 30)
            return wait.until(EC.presence_of_element_located((By.XPATH, x)))
        except:
            return False

    map_searach_box = b.driver.find_element(By.XPATH,("//div[@class='gstl_50 sbib_a']//input[@id='searchboxinput']"))
    map_searach_box.send_keys("Best Web Design & Development Company in Bangladesh")
    map_searach_box.send_keys(Keys.ENTER)

    a_all = waits(b.driver,"//a[@class='hfpxzc']")
    name_list = []
    review_list = []
    star_list = []

    for a in a_all:
        time.sleep(5)
        a.click()
        time.sleep(5)

        all_review_link = wait(b.driver,"//span[@class='mgr77e']")
        all_review_link.click()

        time.sleep(3)
        average_review = b.driver.find_element(By.XPATH,("//div[@class='fontDisplayLarge']"))
        print(average_review.text)

        time.sleep(3)
        totall_review = b.driver.find_element(By.XPATH,("//div[@class='fontBodySmall']"))
        print(totall_review.text)
        print("-------------------------------------------")

        time.sleep(3)   
        names = b.driver.find_elements(By.XPATH,("//div[@class='d4r55']//span"))
        for name in names:
            name_list.append(name.text)

        review_texts = b.driver.find_elements(By.XPATH,("//span[@class='wiI7pd']"))
        for review_text in review_texts:
            review_list.append(review_text.text)

        star_marks = b.driver.find_elements(By.XPATH,("//span[@class='kvMYJc']"))
        for star in star_marks:
            star_list.append(star.get_attribute("aria-label"))
    

        review = {
            'name': name_list,
            'para': review_list,
            'star': star_list,
            }

        json_dump = json.dumps(review)

        with open("google_map.json", "w") as f:
            f.write(json_dump)



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