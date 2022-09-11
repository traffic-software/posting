import time
from selenium.webdriver.support.select import Select
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

options = webdriver.ChromeOptions()
options.add_argument("user-data-dir=C:\\Users\\Md Alamin Hossain\\Desktop\\Selenium\\profile\\9999")
driver = webdriver.Chrome("C:\\Users\\Md Alamin Hossain\\Downloads\\chromedriver_win32\\chromedriver",options=options)
driver.maximize_window()
driver.get("https://signup.live.com/?lic=1")

create_new_hotmail = driver.find_element(By.XPATH,("//div[@class='form-group-last-child']//a"))
create_new_hotmail.click()
time.sleep(1)

option = driver.find_element(By.XPATH,("//option[@value='hotmail.com']"))
option.click()

input_hotmail_text = driver.find_element(By.XPATH,("//div[@class='row']//input"))
input_hotmail_text.send_keys("next_button_final")

next_button = driver.find_element(By.XPATH,("//div[@class='inline-block']//input[@type='submit']"))
next_button.click()

time.sleep(5)
password_input = driver.find_element(By.XPATH,("//input[@type='password']"))
password_input.send_keys("pass808709")
next_button = driver.find_element(By.XPATH,("//div[@class='inline-block']//input[@type='submit']"))
next_button.click()

time.sleep(2)

first_name = driver.find_element(By.XPATH,("//div[@class='row']//input[@id='FirstName']"))
first_name.send_keys("test")

last_name = driver.find_element(By.XPATH,("//div[@class='row']//input[@id='LastName']"))
last_name.send_keys("one")

next_button = driver.find_element(By.XPATH,("//div[@class='inline-block']//input[@type='submit']"))
next_button.click()

#birth_month
time.sleep(3)
month = driver.find_element(By.ID,"BirthMonth")
mdb = Select(month)
mdb.select_by_visible_text('April')

#birth_day
time.sleep(2)
day = driver.find_element(By.ID,"BirthDay")
bday=Select(day)
bday.select_by_visible_text('6')


#birth_year
time.sleep(2)
bd_year = driver.find_element(By.XPATH,("//input[@type='number']"))
bd_year.send_keys("1997")
next_button = driver.find_element(By.XPATH,("//div[@class='inline-block']//input[@type='submit']"))
next_button.click()

