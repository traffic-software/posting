import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from number1 import number

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(executable_path="C:\\Users\Md Alamin Hossain\\Downloads\\chromedriver_win32\chromedriver")
driver.maximize_window()
driver.get("https://login.aol.com/?src=fp-us&client_id=dj0yJmk9ZXRrOURhMkt6bkl5JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWQ2&crumb=lErcIbXyggQ&intl=us&redirect_uri=https%3A%2F%2Foidc.www.aol.com%2Fcallback&pspid=1197803361&activity=default&done=https%3A%2F%2Fapi.login.aol.com%2Foauth2%2Fauthorize%3Fclient_id%3Ddj0yJmk9ZXRrOURhMkt6bkl5JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWQ2%26intl%3Dus%26nonce%3DUW6GKeJ5DjdDQ278GWFciVrnrmB1keyY%26redirect_uri%3Dhttps%253A%252F%252Foidc.www.aol.com%252Fcallback%26response_type%3Dcode%26scope%3Dmail-r%2Bopenid%2Bopenid2%2Bsdps-r%26src%3Dfp-us%26state%3DeyJhbGciOiJSUzI1NiIsImtpZCI6IjZmZjk0Y2RhZDExZTdjM2FjMDhkYzllYzNjNDQ4NDRiODdlMzY0ZjcifQ.eyJyZWRpcmVjdFVyaSI6Imh0dHBzOi8vd3d3LmFvbC5jb20vIn0.hlDqNBD0JrMZmY2k9lEi6-BfRidXnogtJt8aI-q2FdbvKg9c9EhckG0QVK5frTlhV8HY7Mato7D3ek-Nt078Z_i9Ug0gn53H3vkBoYG-J-SMqJt5MzG34rxdOa92nZlQ7nKaNrAI7K9s72YQchPBn433vFbOGBCkU_ZC_4NXa9E")


create_account = driver.find_element(By.XPATH,("//div[@class='bottom-links-container has-social-buttons']//p//a"))
create_account.click()
time.sleep(2)
first_name = driver.find_element(By.XPATH,("//input[@id='usernamereg-firstName']"))
first_name.send_keys("ssff")
time.sleep(2)
last_name = driver.find_element(By.XPATH,("//div[@class='last-name pure-u-1-2']//input[@id='usernamereg-lastName']"))
last_name.send_keys("hhgg")

time.sleep(2)
email_name = driver.find_element(By.XPATH,("//input[@id='usernamereg-yid']"))
email_name.send_keys("ddddf55")

time.sleep(2)
email_name = driver.find_element(By.XPATH,("//input[@id='usernamereg-password']"))
email_name.send_keys("sm55555@#")

time.sleep(2)
pva = number('eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjY0MzYwOTEsImlhdCI6MTYzNDkwMDA5MSwicmF5IjoiY2MzNzRmNTM3MTUyMDc3MWZjODAyNWM1MTM5OWIzYWUiLCJzdWIiOjIzMTAyOH0.OOd17iPERjvtNLc6KNa15nnG5hKXvkzeBf7aJa0ApMjWoO9on4NMC4UIbJRgJ8CtVk2dk7mVi5JwzC1e_zZXis-M2sx1GsFRgWum7BIlyxhYWYYp2rAJuW7YrcAn5MWBXC7E2DaKeeVonDgwzN1_FlUAEnS1iggGgdeKtTy3YZ75mH1z3lrsjjbml_vvP2PrCdpjEl7x2EXBizng3NNxqG72rF9OwI8I5mJj1ks0oHbdMNqOdScdExG6a9MJj9NXOFQmBx9C9bTgCCkhcd1T5bmX5-royaHq8LEyZnuE9HXMwo3mHL_Nny3mwCwftC95dMUqNARrQkY5p0hK4OUQfg','spain','any','aol')

buy_number = pva.buy_number()
country_code = pva.country_c
print(buy_number)

time.sleep(2)
country_list = driver.find_element(By.XPATH,("//select[@name='shortCountryCode']"))
optionss =  country_list.find_element(By.XPATH,"//option[@data-code='{0}']".format(country_code))
optionss.click()

time.sleep(2)
country_number = driver.find_element(By.XPATH,("//input[@id='usernamereg-phone']"))
country_number.send_keys('{0}'.format(buy_number)) 

#birth_month
time.sleep(2)
month = driver.find_element(By.ID,"usernamereg-month")
mdb = Select(month)
mdb.select_by_visible_text('April')

#birth_day
time.sleep(2)
day = driver.find_element(By.XPATH,("//input[@id='usernamereg-day']"))
day.send_keys("6")
#birth_year
time.sleep(2)
bd_year = driver.find_element(By.XPATH,("//input[@id='usernamereg-year']"))
bd_year.send_keys("1997")

next_click = driver.find_element(By.XPATH,("//button[@id='reg-submit-button']"))
next_click.click()


time.sleep(5)
try:
    recaptcha = driver.find_element(By.XPATH,("//div[@class='recaptcha-checkbox-borderAnimation']"))
    time.sleep(2)
    recaptcha.click()
except:
    pass

time.sleep(2)
send_code = driver.find_element(By.XPATH,("//button[@name='sendCode']"))
send_code.click()

time.sleep(2)
code_field = driver.find_element(By.XPATH,("//input[@id='verification-code-field']"))
if code_field:
    check_sms = pva.check_sms()
    print(check_sms)
    print(check_sms["code"])
    code = check_sms["code"]
    
    code_field.send_keys('{0}'.format(code))



time.sleep(1000)

