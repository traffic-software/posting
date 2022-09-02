import time
import random
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
driver = webdriver.Chrome(executable_path="C:\\Users\Md Alamin Hossain\\Downloads\\chromedriver_win32\chromedriver")
driver.maximize_window()
d =driver.get("https://www.google.com/maps")

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

map_searach_box = driver.find_element(By.XPATH,("//div[@class='gstl_50 sbib_a']//input[@id='searchboxinput']"))
map_searach_box.send_keys("Best Web Design & Development Company in Bangladesh")
map_searach_box.send_keys(Keys.ENTER)

a_all = waits(driver,"//a[@class='hfpxzc']")
name_list = []
review_list = []
star_list = []

for a in a_all:
    time.sleep(5)
    a.click()
    time.sleep(5)
    all_review_link = wait(driver,"//span[@class='mgr77e']")
    # all_review_link = driver.find_element(By.XPATH,("//span[@class='mgr77e']"))
    # time.sleep(5)
    all_review_link.click()

    time.sleep(3)
    average_review = driver.find_element(By.XPATH,("//div[@class='fontDisplayLarge']"))
    

    time.sleep(3)
    totall_review = driver.find_element(By.XPATH,("//div[@class='fontBodySmall']"))
    print(totall_review.text)
    print("-------------------------------------------")

    time.sleep(3)   
    names = driver.find_elements(By.XPATH,("//div[@class='d4r55']//span"))
    for name in names:
        # print("---------review_name:--------------")
        # print(name.text)
        name_list.append(name.text)

    review_texts = driver.find_elements(By.XPATH,("//span[@class='wiI7pd']"))
    for review_text in review_texts:
        # print("---------review_text:------------")
        # print(review_text.text)
        review_list.append(review_text.text)

    star_marks = driver.find_elements(By.XPATH,("//span[@class='kvMYJc']"))
    for star in star_marks:
        star_list.append(star.get_attribute("aria-label"))
   

    review = pd.DataFrame(
        {'name': name_list,
        'para': review_list,
        'star': star_list,
        })

    # data =json.loads(review)
    # print(review)

    data = review.to_json(orient='table')
    print(data)






