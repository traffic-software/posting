import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
options = webdriver.ChromeOptions()
options.add_argument("user-data-dir=C:\\Users\\Md Alamin Hossain\\Desktop\\Selenium\\prfile\\1234")

driver = webdriver.Chrome(executable_path="C:\\Users\Md Alamin Hossain\\Downloads\\chromedriver_win32\chromedriver",options=options)
driver.maximize_window()
driver.get("https://www.linkedin.com/checkpoint/lg/sign-in-another-account")
if 'com/feed' not in driver.current_url:
    username = driver.find_element(By.XPATH,("//input[@id='username']"))
    username.send_keys("butter1@arxxwalls.com")

    password = driver.find_element(By.XPATH,("//input[@id='password']"))
    password.send_keys("sm808709@")

    login = driver.find_element(By.CSS_SELECTOR,("button[type='submit']"))
    login.click()




def searchJob():
    
    application_outlet = driver.find_element(By.CSS_SELECTOR,("div[class='application-outlet']"))
    header_id = application_outlet.find_element(By.CSS_SELECTOR,("header[id='global-nav']"))
    search_text = header_id.find_element(By.CSS_SELECTOR,("input[class='search-global-typeahead__input always-show-placeholder']"))
    search_text.send_keys('Job')
    search_text.send_keys(Keys.ENTER)
    time.sleep(3)




def join_group():

    search_filter = driver.find_element(By.XPATH,("//div[@id='search-reusables__filters-bar']"))
    job_group = search_filter.find_element(By.XPATH,("//button[text()='Groups']"))
    job_group.click()
    time.sleep(3)
    group_link = driver.find_element(By.XPATH,("//div[@class='ph0 pv2 artdeco-card mb2']"))
    link = group_link.find_elements(By.TAG_NAME,("a"))
    type(link)
    random_link = random.choice(link)
    random_link.click()
    time.sleep(1)

    join= False
    try:
        join = driver.find_element(By.XPATH,("//span[text()='Join']"))
        join.click()
    except:
        join=False

    time.sleep(3)
   

def follow_company():
    searchJob()
    search_filter = driver.find_element(By.XPATH,("//div[@id='search-reusables__filters-bar']"))
    job_group = search_filter.find_element(By.XPATH,("//button[text()='Companies']"))
    job_group.click()
    time.sleep(3)
    group_link = driver.find_element(By.XPATH,("//div[@class='ph0 pv2 artdeco-card mb2']"))
    link = group_link.find_elements(By.XPATH,("//li[@class='reusable-search__result-container ']"))
    type(link)
    random_link = random.choice(link)
    random_link.click()
    time.sleep(3)

    follow= False
    try:
        follow = driver.find_element(By.XPATH,("//span[text()='Follow']"))
        follow.click()
    except:
        follow=False

    time.sleep(3)
   

def addNewPeople():
    link_list= ["https://www.linkedin.com/in/danielle-kle/","https://www.linkedin.com/in/ACwAABFwffoBx4h-GBP_fB-zH13o-0JC1u6RTOI/"]



    for link in link_list:
        profile = driver.get(link)
        time.sleep(3)
        
        print('.................................................')
        msg_element =driver.find_element(By.XPATH,("//div[@class='pvs-profile-actions ']"))
        
        locked=False
        try:
            locked =msg_element.find_element(By.CSS_SELECTOR,('[type="locked"]'))
        except:
            
            locked=False

        if(locked):
            element2 = driver.find_element(By.XPATH,("//div[@class='pvs-profile-actions ']//span[text()='More']"))
            element2.click()
            # print(element2.get_attribute('innerHTML'))

            more_bt = driver.find_element(By.XPATH,("//div[@class='ph5 pb5']//span[text()='More']"))
            more_bt.click()

            connects = driver.find_element(By.XPATH,("//div[@class='ph5 pb5']//span[text()='Connect']"))
            connects.click()

            add_a_note = driver.find_element(By.XPATH,("//span[text()='Add a note']"))
            add_a_note.click()

            add_a_note_text = driver.find_element(By.XPATH,("//textarea[@id='custom-message']"))
            add_a_note_text.click()

            add_write_msg = driver.find_element(By.TAG_NAME,("textarea"))
            add_write_msg.send_keys("testing")


            add_a_note_send = driver.find_element(By.XPATH,("//span[text()='Send']"))
            add_a_note_send.click()
            

            time.sleep(3)
            
        else:
            msg_element1 =driver.find_element(By.XPATH,('//div[@class="ph5 pb5"]//a[text()="Message"]'))
            print(msg_element1.get_attribute('innerHTML'))
            msg_element1.click()
            time.sleep(3)

            text_msg = driver.find_elements(By.XPATH,('//div[@class="flex-grow-1"]'))[-1]
            # print(text_msg.get_attribute('innerHTML'))
            text_msg.click()

            write_msg = text_msg.find_element(By.TAG_NAME,("p"))
            write_msg.send_keys("testing")
            # print(write_msg.get_attribute('innerHTML'))
            time.sleep(3)
            # send_bt = driver.find_element(By,"//button[text()='Send']").click()

            bt_send = driver.find_element(By.CSS_SELECTOR,("button[type='submit']"))
            bt_send.click()
            # print(bt_send.get_attribute('innerHTML'))

        

def message_work():
    msg_container = driver.find_elements(By.CSS_SELECTOR,'.msg-conversations-container__conversations-list>div')

    # print(msg_container.get_attribute('innerHTML'))

    for all_msg in msg_container:
        print(all_msg.get_attribute('innerHTML'))
        print('.........................................')


        unseen_msg=False
        try:
            unseen_msg = all_msg.find_element(By.XPATH,"//div[starts-with(@class,'artdeco-notification-badge')]//span")
        except:
            
            unseen_msg=False

        print(unseen_msg.get_attribute('innerHTML'))
        if (unseen_msg):
            
            unseen_msg.click()

            msg_reciever = driver.find_element(By.XPATH,("//div[starts-with(@class,'msg-convo-wrapper')]//a[starts-with(@id,'ember')]"))
            print('Unseen message Box Area')
            print('.........................................')
            reciever_link = msg_reciever.get_attribute('href')
            print('link : ', reciever_link)

            reciever_name = msg_reciever.text
            print('name : ', reciever_name)

            print('.........................................')
            print('last text box in below')
            print('.........................................')

            messagebox= driver.find_element(By.CLASS_NAME,('msg-s-message-list-content'))
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
            msg_reciever = driver.find_element(By.XPATH,("//div[starts-with(@class,'msg-convo-wrapper')]//a[starts-with(@id,'ember')]"))
            print('Receiver Box Area')
            print('.........................................')
            reciever_link = msg_reciever.get_attribute('href')
            print('link : ', reciever_link)

            reciever_name = msg_reciever.text
            print('name : ', reciever_name)

            print('.........................................')
            print('last text box in below')
            print('.........................................')

            messagebox= driver.find_element(By.CLASS_NAME,('msg-s-message-list-content'))
            lastmess = messagebox.find_elements(By.CLASS_NAME,("msg-s-message-list__event"))[-1]
            last_span_text = lastmess.find_elements(By.CSS_SELECTOR,("span[class='msg-s-message-group__name t-14 t-black t-bold hoverable-link-text']"))[-1]
            last_p_text = lastmess.find_elements(By.XPATH,("//div[@class='msg-s-event__content']//p"))[-1]

            print('Name',last_span_text.text)
            print('Msg',last_p_text.text)


            lastid = messagebox.find_elements(By.XPATH,("//div[@class='msg-s-message-group__meta']//a"))[-1]

            print('lastid : ', lastid.get_attribute('href'))


message_work()
addNewPeople()
follow_company()
join_group()
searchJob()
