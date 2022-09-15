import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from linkedin_num import linkedin_num

driver = webdriver.Chrome(executable_path="C:\\Users\Md Alamin Hossain\\Downloads\\chromedriver_win32\chromedriver")
driver.maximize_window()
driver.get("https://www.linkedin.com/signup")

email_address = driver.find_element(By.XPATH,("//input[@name='email-address']"))
email_address.send_keys("test_one_one1@gmail.com")
time.sleep(2)

password = driver.find_element(By.XPATH,("//input[@id='password']"))
password.send_keys("test_one_one1@")
time.sleep(2)

continue_button = driver.find_element(By.XPATH,("//button[@class='join-form__form-body-submit-button']"))
continue_button.click()
time.sleep(2)

first_name = driver.find_element(By.XPATH,("//input[@id='first-name']"))
first_name.send_keys("test")
time.sleep(2)

last_name = driver.find_element(By.XPATH,("//input[@id='last-name']"))
last_name.send_keys("one")
time.sleep(2)

continue_button = driver.find_element(By.XPATH,("//button[@id='join-form-submit']"))
continue_button.click()
time.sleep(2)

pva = linkedin_num('eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjY0MzYwOTEsImlhdCI6MTYzNDkwMDA5MSwicmF5IjoiY2MzNzRmNTM3MTUyMDc3MWZjODAyNWM1MTM5OWIzYWUiLCJzdWIiOjIzMTAyOH0.OOd17iPERjvtNLc6KNa15nnG5hKXvkzeBf7aJa0ApMjWoO9on4NMC4UIbJRgJ8CtVk2dk7mVi5JwzC1e_zZXis-M2sx1GsFRgWum7BIlyxhYWYYp2rAJuW7YrcAn5MWBXC7E2DaKeeVonDgwzN1_FlUAEnS1iggGgdeKtTy3YZ75mH1z3lrsjjbml_vvP2PrCdpjEl7x2EXBizng3NNxqG72rF9OwI8I5mJj1ks0oHbdMNqOdScdExG6a9MJj9NXOFQmBx9C9bTgCCkhcd1T5bmX5-royaHq8LEyZnuE9HXMwo3mHL_Nny3mwCwftC95dMUqNARrQkY5p0hK4OUQfg','russia','any','linkedin')
buy_number = pva.buy_number()
country_code = pva.country_c
country_n = pva.country_name
print(country_n)
print(buy_number)

time.sleep(5000)

country_list = driver.find_element(By.XPATH,("//select[@name='countryCode']"))
optionss =  country_list.find_element(By.XPATH,"//option[@data-code='{0}']".format(country_n))
optionss.click()
