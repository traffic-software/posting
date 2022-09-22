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
import mysql.connector
import datetime
from datetime import timedelta

today = datetime.datetime.now()
yesterday = today - timedelta(days = 1)


mydb = mysql.connector.connect(
host="localhost",
user="root",
password="",
database="linkdin"
)
mycursor = mydb.cursor(buffered=True)

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = os.path.abspath(os.path.dirname(__file__))

def addNewPeople(b,cookie):
    query = "SELECT * FROM sms_lead WHERE processing_completed=0"
    mycursor.execute(query)

    myresult = mycursor.fetchone()
    link= "https://www.linkedin.com/in/{0}".format(myresult[1])
    print(link,"**************")
    profile = b.driver.get(link)
    print(profile)
    print('.................................................')
    try:
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
                
                #add_a_not Query
                query = "SELECT * FROM sms_message WHERE type=1"
                mycursor.execute(query)
                add_a_note_query = mycursor.fetchone()
                sent_note = add_a_note_query[2]
                add_write_msg = b.driver.find_element(By.TAG_NAME,("textarea"))
                add_write_msg.send_keys("{0}".format(sent_note))

                add_a_note_send = b.driver.find_element(By.XPATH,("//span[text()='Send']"))
                time.sleep(2)
                add_a_note_send.click()
                time.sleep(3)

                
                cookie_id = cookie[0]
                print(cookie_id)

                sql = "INSERT INTO recivemessage (no_id, sms_lead_id,eventType,message_type,message_id,body) VALUES (%s, %s, %s, %s, %s, %s)"
                val = ("{0}".format(cookie_id), "{0}".format(myresult[0]),"out","{0}".format(add_a_note_query[3]),"{0}".format(add_a_note_query[0]),"{0}".format(add_a_note_query[2]))
                mycursor.execute(sql, val)
                mydb.commit()
                print("-----------------------Add to note Insert receive table is done----------------")

                username =myresult[1]
                print(username)
                id =myresult[0]
                print(id)
                mycursor.execute("UPDATE sms_lead SET processing_completed = '2', created_at='{0}', updated_at='{1}' WHERE id = {2}".format(today,today,id))
                # print(query)
                mydb.commit()
                print("--------Add a note---------updated is done-----------------------")

        else:
            
            msg_element1 =b.find("//div[@class='ph5 pb5']//a[text()='Message']","msg_element1",try_only=True)
            # print(msg_element1.get_attribute('innerHTML'))
            msg_element1.click()
            time.sleep(3)


            text_msg = b.find("//div[@class='flex-grow-1']//p","text_msg","xpath",try_only=True)

            if text_msg:
                text_msg.click()
                time.sleep(2)
                #sent_message Query
                query = "SELECT * FROM sms_message WHERE type=0"
                mycursor.execute(query)
                sms_message_q = mycursor.fetchone()
                sent_msg = sms_message_q[2]                
                text_msg.send_keys("{0}".format(sent_msg))  
                time.sleep(3)
                bt_send = b.driver.find_element(By.CSS_SELECTOR,("button[type='submit']"))
                time.sleep(2)
                bt_send.click()
                print("--------------------Sent message-----------------------------------")
                # Insert recivemessage table
                
                cookie_id = cookie[0]
                sql = "INSERT INTO recivemessage (no_id, sms_lead_id,eventType,message_type,message_id,body) VALUES (%s, %s, %s, %s, %s, %s)"
                val = ("{0}".format(cookie_id), "{0}".format(myresult[0]),"out","{0}".format(sms_message_q[3]),"{0}".format(sms_message_q[0]),"{0}".format(sms_message_q[2]))
                mycursor.execute(sql, val)
                print("-----------------------Sent message Insert receive table is done----------------")

                #sms_lead table
                id =myresult[0]
                # print(id)
                mycursor.execute("UPDATE sms_lead SET processing_completed = '1', created_at='{0}', updated_at='{1}' WHERE id = {2}".format(today,today,id))
                # print(query)
                mydb.commit()
                print("---------------------updated sms_lead table is done----------------")

            # print(bt_send.get_attribute('innerHTML'))
    except Exception as e:
        print(e)
        print("----------Not found--------------")
        username =myresult[1]
        print(username)
        id =myresult[0]
        print(id)
        mycursor.execute("UPDATE sms_lead SET processing_completed = '3', created_at='{0}', updated_at='{1}' WHERE id = {2}".format(today,today,id))
        # print(query)
        mydb.commit()
        print("-----------Nothing found--------------updated is done------------------------")
        
def message_work(b,cookie):
    msg_container = b.driver.find_elements(By.CSS_SELECTOR,'.msg-conversations-container__conversations-list>div')

    # print(msg_container.get_attribute('innerHTML'))

    for all_msg in msg_container:
        # print(all_msg.get_attribute('innerHTML'))
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
            try: 
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
                break
            except:
                pass

def searchJob(b,cookie):

    application_outlet = b.driver.find_element(By.CSS_SELECTOR,("div[class='application-outlet']"))
    header_id = application_outlet.find_element(By.CSS_SELECTOR,("header[id='global-nav']"))
    search_text = header_id.find_element(By.CSS_SELECTOR,("input[class='search-global-typeahead__input always-show-placeholder']"))
    search_text.send_keys('Job')
    time.sleep(2)
    search_text.send_keys(Keys.ENTER)
    time.sleep(3)

def join_group(b,cookie):
    time.sleep(5)
    search_filter = b.driver.find_element(By.XPATH,("//div[@id='search-reusables__filters-bar']"))
    job_group = search_filter.find_element(By.XPATH,("//button[text()='Groups']"))
    job_group.click()
    time.sleep(5)
    group_link = b.driver.find_element(By.XPATH,("//div[@class='ph0 pv2 artdeco-card mb2']"))
    link = group_link.find_elements(By.TAG_NAME,("a"))
    
    random_link = random.choice(link)

    time.sleep(2)
    random_link.click()
    time.sleep(2)

    join= False
    try:
        join = b.driver.find_element(By.XPATH,("//button[@class='white-space-nowrap mt4 artdeco-button artdeco-button--2 artdeco-button--primary ember-view']"))
        print(join.text,"----------Group Join------------")
        join.click()
        time.sleep(3)
    except:
        join=False

    time.sleep(3)

def follow_company(b,cookie):
    searchJob(b,cookie)
    search_filter = b.driver.find_element(By.XPATH,("//div[@id='search-reusables__filters-bar']"))
    job_group = search_filter.find_element(By.XPATH,("//button[text()='Companies']"))
    job_group.click()
    time.sleep(3)
    group_link = b.driver.find_element(By.XPATH,("//div[@class='ph0 pv2 artdeco-card mb2']"))
    link = group_link.find_elements(By.XPATH,("//li[@class='reusable-search__result-container ']"))
    type(link)
    time.sleep(2)
    random_link = random.choice(link)
    random_link.click()
    time.sleep(3)

    follow= False
    try:
        follow =b.driver.find_element(By.XPATH,("//span[text()='Follow']"))
        print(follow.text,"Follow-------------------")
        time.sleep(3)
        follow.click()
        time.sleep(3)
    except:
        follow=False
    time.sleep(3)

def write_cookies(b,cookie):
    pickle.dump(b.driver.get_cookies() , open(cookie[2],"wb"))
    print("------------Cookies is updated--------------")
    for item in b.driver.get_cookies():
        print(item)
    sms_no_id = cookie[0]

    sql = "UPDATE sms_no SET cookie_time = '{0}', updated_at='{1}' WHERE id = '{2}'".format(today,today,sms_no_id)
    mycursor.execute(sql)
    mydb.commit()
    print("------------SMS_NO table is updated--------------")






def main(account_data, postinfo, packages_id, body_mail):
    # work start time


    # starttime = datetime.now()
    print(account_data)
    postinfo = postinfo.get_post(account_data['id'])

    print(postinfo)



    # print(datetime.now().strftime("%H:%M:%S"))

    account_id = account_data['id']


    b = browser(account_id, pva=account_data)


    time.sleep(5)
    # if b.PROXY_PASS == False:
    #     b.exit()
    #     print('proxy condition not fulfilled')
    #     # worker_acc.ban_3(account_id, 5)
    #     time.sleep(10)
    #     return False

    #start your work
    mycursor = mydb.cursor()
    query = "SELECT * FROM sms_no WHERE `cookie_time` LIKE '%{0}%'".format(yesterday)
    mycursor.execute(query)
    cookie = mycursor.fetchone()
    try:
        b.driver.get("https://www.linkedin.com/feed/")
        time.sleep(5)
        load_cookies = pickle.load(open(cookie[2], "rb"))
        for load_cookie in load_cookies:
            print(load_cookie)
            b.driver.add_cookie(load_cookie)
            print("add cookie")
        time.sleep(5)     
        b.driver.get("https://www.linkedin.com/feed/")
    except:
        b.exit()
    # b.driver.get("https://www.linkedin.com/checkpoint/lg/sign-in-another-account") 
    # def random_name():
    #     upper_char ='ABCDEFGHIJKLMNOPSRUVWXYZ'
    #     lower_char ='abcdefghijklmnopsruvwxyz'
    #     string = upper_char+lower_char
    #     length = 20
    #     generator_pass = "".join(random.sample(string,length))
    #     return generator_pass

    # if 'com/feed' not in b.driver.current_url:
    #     username = b.find(("//input[@id='username']"))
    #     username.send_keys("yahoo@emergentvillage.org")

    #     password = b.find(("//input[@id='password']"))
    #     password.send_keys("12345@")

    #     login = b.find(("//button[@type='submit']"))
    #     login.click()
    #     ran_name = random_name()
    #     time.sleep(2)
    #     tag = b.driver.find_element(By.XPATH,("//a[@class='ember-view block']"))
    #     profile_name = tag.text
    #     print("Profile Name: ",profile_name)
    #     pickle.dump( b.driver.get_cookies() , open("{0}.pkl".format(ran_name),"wb"))
    #     for item in b.driver.get_cookies():
    #         print(item)

    #     mycursor = mydb.cursor()
    #     query = "SELECT * FROM sms_no"
    #     mycursor.execute(query)
    #     cookie = mycursor.fetchone()
    #     # mycursor = mydb.cursor()
    #     sql = "INSERT INTO sms_no (name,file,type,cookie_time,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s)"
    #     val = (profile_name,ran_name+".pkl","1","{}".format(cookie[5]),"{}".format(cookie[6]),"{}".format(cookie[7]))
    #     mycursor.execute(sql, val)

    #     mydb.commit()

    #     print(mycursor.rowcount, "record inserted.")

    


    addNewPeople(b,cookie)  
    message_work(b,cookie)       
    searchJob(b,cookie)
    join_group(b,cookie)
    follow_company(b,cookie)  
    write_cookies(b,cookie)  
    
 
    print('browser close')
    # b.ipinfo_save(software_name='google')
    # print(b.driver.get_cookies())

    # print('start :', starttime)
    # print('end :', datetime.now().strftime("%H:%M:%S"))



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