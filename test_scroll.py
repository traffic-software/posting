from selenium import webdriver
import pandas as pd
import time
from selenium.webdriver.common.by import By
driver = webdriver.Chrome(executable_path="C:\\Users\Md Alamin Hossain\\Downloads\\chromedriver_win32\chromedriver")
driver.maximize_window()

url='https://www.google.com.my/maps/place/Mid+Valley+Megamall/@3.1174126,101.6738273,17z/data=!4m7!3m6!1s0x31cc498eb19ab83d:0x564d5053f56991fb!8m2!3d3.1174073!4d101.6780545!9m1!1b1'

driver.get(url)
time.sleep(5)

# driver.find_element(By.XPATH,'//*[@id="QA0Szd"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[7]/div[2]/button').click()

# time.sleep(1)

# driver.find_element(By.XPATH,"//li[@data-index='1']").click()

# time.sleep(5)

SCROLL_PAUSE_TIME = 5

# Get scroll height
last_height = driver.execute_script("return document.body.scrollHeight")

number = 0

while True:
    number = number+1

    # Scroll down to bottom
    
    ele = driver.find_element(By.XPATH,'//div[@class="m6QErb DxyBCb kA9KIf dS8AEf"]')
    driver.execute_script('arguments[0].scrollBy(0, 6000);', ele)

    # Wait to load page

    time.sleep(SCROLL_PAUSE_TIME)

    # Calculate new scroll height and compare with last scroll height
    print(f'last height: {last_height}')

    ele = driver.find_element(By.XPATH,'//div[@class="m6QErb DxyBCb kA9KIf dS8AEf"]')

    new_height = driver.execute_script("return arguments[0].scrollHeight", ele)

    print(f'new height: {new_height}')

    if number == 3:
        break

    if new_height == last_height:
        break

    print('cont')
    last_height = new_height

    

names = driver.find_elements(By.XPATH,"//div[@class='d4r55']")
for n in names:
    print(n.text)