import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from linkedin_num import linkedin_num
import random
import requests

def ran_password():
        characters ="abcdefghijklmnopshwyz"
        upper ="ABCDEFGHIJKLMNOPQPSHWYZ"
        symbol ="@%"
        num = "0123456789"
        string = characters+symbol+num+upper
        length = 8
        password = "".join(random.sample(string,length))
        # print("Random password:",password)
        return password
def get_prices(product = 'google'):
    product = 'google'

    headers = {
        'Accept': 'application/json',
    }

    params = (
        ('product', product),
    )
    response = requests.get('https://5sim.net/v1/guest/prices', headers=headers, params=params)
    items = response.json()[product]
    for i in items:
        
        price=0
        count=0
        fastitem={}
        avarage=0
        for n in items[i].values():
            # print(n)
            price +=n['cost']
            count +=n['count']
            avarage +=1
       
        fastitem['country']=i
        fastitem['avarage ']=price/avarage
        fastitem['count']=count
        print(fastitem)
        print('.............................')

get_prices('google')

# exit()

driver = webdriver.Chrome(executable_path="C:\\Users\Md Alamin Hossain\\Downloads\\chromedriver_win32\chromedriver")
driver.maximize_window()
driver.get("https://www.linkedin.com/signup")

email_address = driver.find_element(By.XPATH,("//input[@name='email-address']"))
email_address.send_keys("test_one_one1@gmail.com")
# email_address.send_keys("test_one_one1@gmail.com")
time.sleep(2)

password = driver.find_element(By.XPATH,("//input[@id='password']"))
pwd = ran_password()
print("password:",pwd)
password.send_keys(pwd)
# password.send_keys("test_one_one1@")
time.sleep(5)

continue_button = driver.find_element(By.XPATH,("//button[@class='join-form__form-body-submit-button']"))
continue_button.click()
time.sleep(2)

first_name = driver.find_element(By.XPATH,("//input[@id='first-name']"))
first_name.send_keys("test")
time.sleep(1)

last_name = driver.find_element(By.XPATH,("//input[@id='last-name']"))
last_name.send_keys("one")
time.sleep(1)

continue_button = driver.find_element(By.XPATH,("//button[@id='join-form-submit']"))
continue_button.click()

pva = linkedin_num('eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjY0MzYwOTEsImlhdCI6MTYzNDkwMDA5MSwicmF5IjoiY2MzNzRmNTM3MTUyMDc3MWZjODAyNWM1MTM5OWIzYWUiLCJzdWIiOjIzMTAyOH0.OOd17iPERjvtNLc6KNa15nnG5hKXvkzeBf7aJa0ApMjWoO9on4NMC4UIbJRgJ8CtVk2dk7mVi5JwzC1e_zZXis-M2sx1GsFRgWum7BIlyxhYWYYp2rAJuW7YrcAn5MWBXC7E2DaKeeVonDgwzN1_FlUAEnS1iggGgdeKtTy3YZ75mH1z3lrsjjbml_vvP2PrCdpjEl7x2EXBizng3NNxqG72rF9OwI8I5mJj1ks0oHbdMNqOdScdExG6a9MJj9NXOFQmBx9C9bTgCCkhcd1T5bmX5-royaHq8LEyZnuE9HXMwo3mHL_Nny3mwCwftC95dMUqNARrQkY5p0hK4OUQfg'
,'pakistan','any','linkedin')
buy_number = pva.buy_number()
country_code = pva.country_c
country_n = pva.country_name
print(country_n)
print(buy_number)
time.sleep(2)

iframe = driver.find_elements(By.TAG_NAME,'iframe')[1]
driver.switch_to.frame(iframe)
country_list = driver.find_element(By.XPATH,("/html/body/div/main/form/div[1]/select"))
time.sleep(2)
optionss = country_list.find_element(By.XPATH,("//option[@extension=' {0} ']".format(country_code)))
optionss.click()

phn_number = driver.find_element(By.XPATH,("//input[@name='phoneNumber']"))
phn_number.send_keys("{0}".format(buy_number))
submit_button = driver.find_element(By.XPATH,("//button[@id='register-phone-submit-button']"))
submit_button.click()

try:
    verify_code = driver.find_element(By.XPATH,("//input[@class='form__input--text input_verification_pin']"))
    check_sms=pva.check_sms()
    verify_code.send_keys('{0}'.format(check_sms))
    submit_button = driver.find_element(By.XPATH,("//button[@id='join-form-submit']"))
    # # text_file_write
    # f = open("linkedin.txt", "a")
    # f.write("{0}:{1}:{2}:{3}\n".format(first_name,last_name,values,pwd))
    # f.close()
    # #open and read the file after the appending:
    # f = open("linkedin.txt", "r")
    # print(f.read())
except:
    pass

time.sleep(2000)
