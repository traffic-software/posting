import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import time
driver = webdriver.Chrome("C:\\Users\\Md Alamin Hossain\\Downloads\\chromedriver_win32\\chromedriver")
driver.maximize_window()
driver.get("https://www.google.com/")
import math

def checkTimeOut(starttime,workerTimeOut=5):
    
    fmt = '%Y-%m-%d %H:%M:%S'
    now = datetime.now()
    d1 = datetime.strptime(starttime.strftime(fmt), fmt)
    d2 = datetime.strptime(now.strftime(fmt), fmt)


    # Convert to Unix timestamp
    d1_ts = time.mktime(d1.timetuple())
    d2_ts = time.mktime(d2.timetuple())
    d1_ts = time.mktime(d1.timetuple())

    # They are now in seconds, subtract and then divide by 60 to get minutes.
    ruinngtime= d2_ts-d1_ts
    print('software runing in ',ruinngtime)
    workerTimeOut=workerTimeOut*60
    if workerTimeOut<ruinngtime:
        return True

def scrolling():
    total_height = int(driver.execute_script(
    "return document.body.scrollHeight"))
    
    
    total = total_height / random.choice([2, 3, 4, 7, 1])
    

    for i in range(1, round(total), 1):
        time.sleep(0.02)
        driver.execute_script("window.scrollTo(0, {});".format(i))
def nextclick():
    
    
    target_site_link = driver.find_elements(By.XPATH,("//div[@class='single-content2']//a[contains(@href,'https://datasuk')]"))
    randon_link = random.choice(target_site_link)
    driver.get(randon_link.get_attribute('href'))
    # randon_link.click()
workerTimeOut =random.choice([3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20])

starttime = datetime.now()
def target_site():
    if checkTimeOut(starttime,workerTimeOut):
        return True
    if random.choice([2,3,1]) ==1:
        scrolling()
        nextclick()
        target_site()
    if random.choice([2,3,1]) ==2:
        
        nextclick()
        scrolling()
        target_site()
    if random.choice([2,3,1]) ==3:
        
        nextclick()
        scrolling()
    
        comment_text_area = driver.find_element(By.XPATH,("//div[@class='comment-form wow fadeIn animated']//textarea"))
        comment_text_area.send_keys("Hi! I am new in here.")

        comment_text_area_name = driver.find_element(By.XPATH,("//div[@class='comment-form wow fadeIn animated']//input[@name='name']"))
        comment_text_area_name.send_keys("SM Samrat")

        comment_text_area_email = driver.find_element(By.XPATH,("//div[@class='comment-form wow fadeIn animated']//input[@name='email']"))
        comment_text_area_email.send_keys("SM@gmail.com")

        comment_text_area_website = driver.find_element(By.XPATH,("//div[@class='comment-form wow fadeIn animated']//input[@name='website']"))
        comment_text_area_website.send_keys("samrat.com")

        comment_text_area_post_comment = driver.find_element(By.XPATH,("//div[@class='comment-form wow fadeIn animated']//button"))
        comment_text_area_post_comment.click()

        target_site()
  
    time.sleep(2)
    return True
    
    
    # driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

google = driver.find_element(By.XPATH,("//input[@class='gLFyf gsfi']"))
google.send_keys("web developer salary nyc ")
google.send_keys(Keys.ENTER)
avarage_position = 165
page = round((avarage_position+50)/10,2)
runing_page = 0

    
while True:
    target_link= False
    try:
        target_link = driver.find_element(By.XPATH,"//a[contains(@href,'https://datasuk')]")
        if target_link:
            target_link.click()
            time.sleep(5)
            target_site()
            driver.quit()
            break
    except:
        print('next page : ',runing_page)
        runing_page =runing_page+1
        if runing_page>page:
            break
        next_page_link = driver.find_element(By.XPATH,'//*[@id="pnnext"]')
        next_page_link.click()
