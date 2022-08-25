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

        b.get_url('https://www.google.com')
    except:
        time.sleep(200)
        b.exit()

    # def waits(driver,x):

    #     try:
    #         wait = WebDriverWait(driver, 30)
    #         return wait.until(EC.presence_of_all_elements_located((By.XPATH, x)))
    #     except:
    #         return False

    def wait(driver,x):

        try:
            wait = WebDriverWait(driver, 30)
            return wait.until(EC.presence_of_element_located((By.XPATH, x)))
        except:
            return False

    map_searach_box = b.driver.find_element(By.XPATH,("//input[@class='gLFyf gsfi']"))
    map_searach_box.send_keys("Best Web Design & Development Company in Bangladesh")
    map_searach_box.send_keys(Keys.ENTER)

    more_business = b.driver.find_element(By.XPATH,("//div[@class='MXl0lf tKtwEb wHYlTd']//span"))
    more_business.click()
    time.sleep(5)
    div_all = b.driver.find_elements(By.XPATH,"//div[@class='VkpGBb']")
    name_list = []
    review_list = []
    star_list = []

    for div in div_all:
        try:
            # website = div.find_element(By.XPATH,"//span[contains(text(),'SHELLSOFT TECHNOLOGIES')]")
            # print(website.text)
            if 'SHELLSOFT TECHNOLOGIES' in div.text:
                print('intarget')

                # time.sleep(300)   
                div.click()

                time.sleep(3)
                average_review = b.driver.find_element(By.XPATH,("//span[@class='fzTgPe Aq14fc']"))
                print(average_review.text)

                time.sleep(3)
                totall_review = b.driver.find_element(By.XPATH,("//span[@class='z5jxId']"))
                print(totall_review.text)
                print("-------------------------------------------")

                all_review_link = wait(b.driver,"//span[@class='hqzQac']//span")
                all_review_link.click()

                time.sleep(5)
                SCROLL_PAUSE_TIME = 5

                # Get scroll height
                last_height = b.driver.execute_script("return document.body.scrollHeight")

                number = 0

                while True:
                    number = number+1

                    # Scroll down to bottom
                    
                    ele = b.driver.find_element(By.XPATH,'//div[@class="review-dialog-list"]')
                    b.driver.execute_script('arguments[0].scrollBy(0, 6000);', ele)

                    # Wait to load page
                    time.sleep(SCROLL_PAUSE_TIME)

                    # Calculate new scroll height and compare with last scroll height
                    print(f'last height: {last_height}')

                    ele = b.driver.find_element(By.XPATH,'//div[@class="review-dialog-list"]')

                    new_height = b.driver.execute_script("return arguments[0].scrollHeight", ele)

                    print(f'new height: {new_height}')

                    if number == 3:
                        break

                    if new_height == last_height:
                        break

                    print('cont')
                    last_height = new_height
                time.sleep(3)   
                names = b.driver.find_elements(By.XPATH,("//div[@class='TSUbDb']"))
                for name in names:
                    # print("---------review_name:--------------")
                    # print(name.text)
                    name_list.append(name.text)

                time.sleep(3)   
                review_texts = b.driver.find_elements(By.XPATH,("//div[@class='Jtu6Td']"))
                for review_text in review_texts:
                    # print("---------review_text:------------")
                    # print(review_text.text)
                    review_list.append(review_text.text)

                time.sleep(3)   
                star_marks = b.driver.find_elements(By.XPATH,("//span[@class='Fam1ne EBe2gf']"))
                for star in star_marks:
                    star_list.append(star.get_attribute("aria-label"))
            

                review ={
                    'name': name_list,
                    'para': review_list,
                    'star': star_list,
                    }
                print(review)
                json_dump = json.dumps(review)

                with open("sample.json", "w") as f:
                    f.write(json_dump)
                time.sleep(5)
                close = b.driver.find_elements(By.XPATH,("//div[@class='Xvesr']"))[-1]
                close.click()
                time.sleep(5)
                website_click = b.driver.find_elements(By.XPATH,("//a[@class='ab_button CL9Uqc']"))[0]
                website_click.click()
                break
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