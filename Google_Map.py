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
d =driver.get("https://www.google.com")

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

map_searach_box = driver.find_element(By.XPATH,("//input[@class='gLFyf gsfi']"))
map_searach_box.send_keys("Best Web Design & Development Company in Bangladesh")
map_searach_box.send_keys(Keys.ENTER)

more_business = driver.find_element(By.XPATH,("//div[@class='MXl0lf tKtwEb wHYlTd']//span"))
more_business.click()
time.sleep(5)
div_all = driver.find_elements(By.XPATH,"//div[@class='VkpGBb']")
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
            average_review = driver.find_element(By.XPATH,("//span[@class='fzTgPe Aq14fc']"))
            # print(average_review.text)

            time.sleep(3)
            totall_review = driver.find_element(By.XPATH,("//span[@class='z5jxId']"))
            print(totall_review.text)
            print("-------------------------------------------")

            all_review_link = wait(driver,"//span[@class='hqzQac']//span")
            all_review_link.click()

            time.sleep(5)
            SCROLL_PAUSE_TIME = 5

            # Get scroll height
            last_height = driver.execute_script("return document.body.scrollHeight")

            number = 0

            while True:
                number = number+1

                # Scroll down to bottom
                
                ele = driver.find_element(By.XPATH,'//div[@class="review-dialog-list"]')
                driver.execute_script('arguments[0].scrollBy(0, 6000);', ele)

                # Wait to load page
                time.sleep(SCROLL_PAUSE_TIME)

                # Calculate new scroll height and compare with last scroll height
                print(f'last height: {last_height}')

                ele = driver.find_element(By.XPATH,'//div[@class="review-dialog-list"]')

                new_height = driver.execute_script("return arguments[0].scrollHeight", ele)

                print(f'new height: {new_height}')

                if number == 3:
                    break

                if new_height == last_height:
                    break

                print('cont')
                last_height = new_height
            time.sleep(3)   
            names = driver.find_elements(By.XPATH,("//div[@class='TSUbDb']"))
            for name in names:
                # print("---------review_name:--------------")
                # print(name.text)
                name_list.append(name.text)

            time.sleep(3)   
            review_texts = driver.find_elements(By.XPATH,("//div[@class='Jtu6Td']"))
            for review_text in review_texts:
                # print("---------review_text:------------")
                # print(review_text.text)
                review_list.append(review_text.text)

            time.sleep(3)   
            star_marks = driver.find_elements(By.XPATH,("//span[@class='Fam1ne EBe2gf']"))
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
            close = driver.find_elements(By.XPATH,("//div[@class='Xvesr']"))[-1]
            close.click()
            time.sleep(5)
            website_click = driver.find_elements(By.XPATH,("//a[@class='ab_button CL9Uqc']"))[0]
            website_click.click()
            break
    except:
        website=False





