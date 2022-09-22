import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
import pickle

driver = webdriver.Chrome(executable_path="C:\\Users\Md Alamin Hossain\\Downloads\\chromedriver_win32\chromedriver")
driver.maximize_window()
driver.get("https://www.linkedin.com/")






input('pls login a account then type y')
pickle.dump( driver.get_cookies() , open("cookies.pkl","wb"))
for item in driver.get_cookies():
    print(item)



