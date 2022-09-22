from selenium import webdriver
import pickle
import time
driver = webdriver.Chrome(executable_path="C:\\Users\Md Alamin Hossain\\Downloads\\chromedriver_win32\chromedriver")
driver.maximize_window()
driver.get("https://www.linkedin.com/")
time.sleep(5)
cookies = pickle.load(open("jAmGgVeENZHfLXUFSdKw.pkl", "rb"))
for cookie in cookies:
    print(cookie)
    # cookie['domain']= '.linkedin.com'
    driver.add_cookie(cookie)
    print("add cookie")
time.sleep(5)
driver.get("https://www.linkedin.com/feed/")