

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
import pickle
from selenium.webdriver.support.select import Select

from datetime import date
from datetime import timedelta
import mysql.connector

mydb = mysql.connector.connect(
host="localhost",
user="root",
password="",
database="linkdin"
)

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = os.path.abspath(os.path.dirname(__file__))



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

        b.get_url('https://www.linkedin.com/checkpoint/lg/sign-in-another-account')
    except:
        b.exit()

    def random_name():
        upper_char ='ABCDEFGHIJKLMNOPSRUVWXYZ'
        lower_char ='abcdefghijklmnopsruvwxyz'
        string = upper_char+lower_char
        length = 20
        generator_pass = "".join(random.sample(string,length))
        return generator_pass

    if 'com/feed' not in b.driver.current_url:
        username = b.find(("//input[@id='username']"))
        username.send_keys("datalink@emergentvillage.org")

        password = b.find(("//input[@id='password']"))
        password.send_keys("123456@")

        login = b.find(("//button[@type='submit']"))
        login.click()
        ran_name = random_name()
        pickle.dump( b.driver.get_cookies() , open("{0}.pkl".format(ran_name),"wb"))
        for item in b.driver.get_cookies():
            print(item)


    time.sleep(5000)

    def searchJob(b):

        application_outlet = b.driver.find_element(By.CSS_SELECTOR,("div[class='application-outlet']"))
        header_id = application_outlet.find_element(By.CSS_SELECTOR,("header[id='global-nav']"))
        search_text = header_id.find_element(By.CSS_SELECTOR,("input[class='search-global-typeahead__input always-show-placeholder']"))
        search_text.send_keys('Job')
        search_text.send_keys(Keys.ENTER)
        time.sleep(3)
    
    def join_group(b):

        search_filter = b.driver.find_element(By.XPATH,("//div[@id='search-reusables__filters-bar']"))
        job_group = search_filter.find_element(By.XPATH,("//button[text()='Groups']"))
        job_group.click()
        time.sleep(3)
        group_link = b.driver.find_element(By.XPATH,("//div[@class='ph0 pv2 artdeco-card mb2']"))
        link = group_link.find_elements(By.TAG_NAME,("a"))
        
        random_link = random.choice(link)

        time.sleep(2)
        random_link.click()
        time.sleep(2)

        join= False
        try:
            join = b.driver.find_element(By.XPATH,("//span[text()='Join']"))
            join.click()
            time.sleep(3)
        except:
            join=False

        time.sleep(3)

    def follow_company(b):
        searchJob(b)
        search_filter = b.driver.find_element(By.XPATH,("//div[@id='search-reusables__filters-bar']"))
        job_group = search_filter.find_element(By.XPATH,("//button[text()='Companies']"))
        job_group.click()
        time.sleep(3)
        group_link = b.driver.find_element(By.XPATH,("//div[@class='ph0 pv2 artdeco-card mb2']"))
        link = group_link.find_elements(By.XPATH,("//li[@class='reusable-search__result-container ']"))
        type(link)
        random_link = random.choice(link)
        random_link.click()
        time.sleep(3)

        follow= False
        try:
            follow =b.driver.find_element(By.XPATH,("//span[text()='Follow']"))
            time.sleep(3)
            follow.click()
            time.sleep(3)
        except:
            follow=False
        time.sleep(3)


    def addNewPeople(b):
        link_list= ["","https://www.linkedin.com/in/{0}"]



        for link in link_list:
            profile = b.driver.get('https://www.linkedin.com/in/'+link)
            time.sleep(3)

            mycursor = mydb.cursor()

            sql = "INSERT INTO sms_no (sms_gete_id,name,file,type,user_id) VALUES (%s,%s,%s,%s,%s)"
            val = ("3","danielle-kle",ran_name+".pkl","2","7")
            mycursor.execute(sql, val)

            mydb.commit()

            print(mycursor.rowcount, "record inserted.")

            print('.................................................')
            msg_element =b.find("//div[@class='pvs-profile-actions ']",'msg_element',"xpath", try_only=True)

            locked=False
            try:
                locked =b.one(msg_element,'[type="locked"]','locked','css', try_only=True)
            except:

                locked=False

            if(locked):
                more_bt = b.find("//div[@class='ph5 pb5']//span[text()='More']","more button","xpath",try_only=True)
                more_bt.click()
                time.sleep(5)
                connects = b.find("//div[@class='ph5 pb5']//span[text()='Connect']","connects","xpath",try_only=True)
                if connects:
                    connects.click()

                    # connects = b.driver.find_element(By.XPATH,("//div[starts-with(@class,'pv-top-card-v2-ctas display-flex')]//span[text()='Connect']"))
                    # connects.click()
                    time.sleep(2)
                    add_a_note = b.driver.find_element(By.XPATH,("//span[text()='Add a note']"))
                    add_a_note.click()

                    add_a_note_text = b.driver.find_element(By.XPATH,("//textarea[@id='custom-message']"))
                    add_a_note_text.click()

                    add_write_msg = b.driver.find_element(By.TAG_NAME,("textarea"))
                    add_write_msg.send_keys("testing")


                    add_a_note_send = b.driver.find_element(By.XPATH,("//span[text()='Send']"))
                    add_a_note_send.click()


                    time.sleep(3)

            else:
                
                msg_element1 =b.find("//div[@class='ph5 pb5']//a[text()='Message']","msg_element1",try_only=True)
                print(msg_element1.get_attribute('innerHTML'))
                msg_element1.click()
                time.sleep(3)


                text_msg = b.find("//div[@class='flex-grow-1']//p","text_msg","xpath",try_only=True)

                if text_msg:
                    text_msg.click()
                    time.sleep(2)
                    text_msg.send_keys("action")

                    time.sleep(3)

                    bt_send = b.driver.find_element(By.CSS_SELECTOR,("button[type='submit']"))
                    bt_send.click()


                # print(bt_send.get_attribute('innerHTML'))
    
    def message_work(b):
        msg_container = b.driver.find_elements(By.CSS_SELECTOR,'.msg-conversations-container__conversations-list>div')

        # print(msg_container.get_attribute('innerHTML'))

        for all_msg in msg_container:
            print(all_msg.get_attribute('innerHTML'))
            print('.........................................')


            unseen_msg=False
            try:
                unseen_msg = all_msg.find_element(By.XPATH,"//div[starts-with(@class,'artdeco-notification-badge')]//span")
            except:

                unseen_msg=False
            if (unseen_msg):

                unseen_msg.click()

                msg_reciever = b.driver.find_element(By.XPATH,("//div[starts-with(@class,'msg-convo-wrapper')]//a[starts-with(@id,'ember')]"))
                print('Unseen message Box Area')
                print('.........................................')
                reciever_link = msg_reciever.get_attribute('href')
                print('link : ', reciever_link)

                reciever_name = msg_reciever.text
                print('name : ', reciever_name)

                print('.........................................')
                print('last text box in below')
                print('.........................................')

                messagebox= b.driver.find_element(By.CLASS_NAME,('msg-s-message-list-content'))
                lastmess = messagebox.find_elements(By.CLASS_NAME,("msg-s-message-list__event"))[-1]
                last_span_text = lastmess.find_elements(By.CSS_SELECTOR,("span[class='msg-s-message-group__name t-14 t-black t-bold hoverable-link-text']"))[-1]
                last_p_text = lastmess.find_elements(By.XPATH,("//div[@class='msg-s-event__content']//p"))[-1]

                print('Name',last_span_text.text)
                print('Msg',last_p_text.text)


                lastid = messagebox.find_elements(By.XPATH,("//div[@class='msg-s-message-group__meta']//a"))[-1]

                print('lastid : ', lastid.get_attribute('href'))

                print('..................End unseen messages.......................')



            else: 
                all_msg.click()
                msg_reciever = b.driver.find_element(By.XPATH,("//div[starts-with(@class,'msg-convo-wrapper')]//a[starts-with(@id,'ember')]"))
                print('Receiver Box Area')
                print('.........................................')
                reciever_link = msg_reciever.get_attribute('href')
                print('link : ', reciever_link)

                reciever_name = msg_reciever.text
                print('name : ', reciever_name)

                print('.........................................')
                print('last text box in below')
                print('.........................................')

                messagebox= b.driver.find_element(By.CLASS_NAME,('msg-s-message-list-content'))
                lastmess = messagebox.find_elements(By.CLASS_NAME,("msg-s-message-list__event"))[-1]
                last_span_text = lastmess.find_elements(By.CSS_SELECTOR,("span[class='msg-s-message-group__name t-14 t-black t-bold hoverable-link-text']"))[-1]
                last_p_text = lastmess.find_elements(By.XPATH,("//div[@class='msg-s-event__content']//p"))[-1]

                print('Name',last_span_text.text)
                print('Msg',last_p_text.text)


                lastid = messagebox.find_elements(By.XPATH,("//div[@class='msg-s-message-group__meta']//a"))[-1]

                print('lastid : ', lastid.get_attribute('href'))
                
    searchJob(b)
    join_group(b)
    follow_company(b)  
    addNewPeople(b)
    message_work(b)    
 












    print('browser close')
    b.ipinfo_save(software_name='google')
    print(b.driver.get_cookies())

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