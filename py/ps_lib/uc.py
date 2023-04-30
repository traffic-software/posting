import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from selenium.webdriver.common.proxy import Proxy, ProxyType
from ps_lib.accounts import accounts
import json
import requests
import os
import time
from ps_lib.ps_str import ps_str
from ps_lib.proxy import ps_proxy
from ps_lib.timezone import t
import sys

import warnings
import random
import string


class ucbrowser:
    account_id = None

    def __init__(self, pofileLocation, use_proxy=True, profile_dir=False, pva=None, image_bock=True, headless=False):

        self.proxy_country = "IT"
        self.proxy_city = None
        self.other_city = None
        self.proxy_region = None
        self.proxy_zip = None
        self.proxy_timezone = None
        self.proxy_latLon = None
        self.proxy_isp = None
        self.proxy_ip = None
        self.proxy_company = 'proxyrotator'
        self.pva = pva
        self.account_id = pofileLocation
        self.use_proxy = use_proxy
        self.image_bock = image_bock
        warnings.filterwarnings('ignore')
        # ................account.....................................
        self.account = accounts()
        # ......................Chrome..............................
        self.options = uc.ChromeOptions()
        


        driverUrl = 'chromedriver'

        self.options.arguments.extend(["--no-sandbox", "--disable-setuid-sandbox"])
        # self.options.add_argument("start-maximized")
          
       
        self.driver = uc.Chrome(options=self.options)
        self.driver.maximize_window()
        # self.driver = uc.Chrome(driver_executable_path=driverUrl, options=self.options, use_subprocess=True)
        # self.driver.set_window_size(500, 600)

    def exit(self):
        try:
            self.driver.quit()
        except:
            print("browser close")

    def get_proxy_zip(self):
        if self.proxy_zip == None:
            return self.get_ipinfo()
        else:
            return self.proxy_zip

    def __del__(self):
        self.exit()

    def checkipused(self, ip, postlog):
        returndata = False
        for i in postlog:

            if ip in i["message"]:
                returndata = True
                break
        return returndata

   
   
    def select_element(self, selector):
        co = 0
        element = False
        while True:
            try:
                element = self.driver.find_element_by_css_selector(selector)
                if element.is_displayed():
                    # print("element ", selector)
                    break
            except:
                co = co+1
                if co > 10:
                    break
                print("waiting for ", selector)
                self.driver.implicitly_wait(1)
        if element == False:
            print("element not find: ", selector)

            self.exit()
            exit()
        return element

    def visibil_element(self, by, selector, wait=30):

        element = False
        if by == 'name':
            byselector = By.NAME
        if by == 'xpath':
            byselector = By.XPATH
        if by == 'css':
            byselector = By.CSS_SELECTOR
        if by == 'id':
            byselector = By.ID
        try:

            element = WebDriverWait(self.driver, wait).until(
                EC.visibility_of_element_located((byselector, selector)))

        except:
            element = False
        if element == False:
            pass
            # print("element not find: ", selector)

        return element

    def try_select_element(self, selector):
        try:
            element = self.driver.find_element_by_css_selector(selector)

            if element.is_displayed() and element.is_enabled():
                print('try_select_element')
                pass

        except:
            element = False

        return element

    def select_elements(self, selector):

        return self.driver.find_elements_by_css_selector(selector)

    def select_element_xpath(self, selector, mesasage="genarl work", type=1, valu=None, wait=1):
       
        co = 0
        element = False
        while True:
            try:
                element = self.driver.find_element_by_xpath(selector)
                if element.is_displayed() and element.is_enabled():
                    print("done : ", mesasage)
                    if type == 2:
                        self.captcha_good(valu)
                    break

            except:
                co = co + 1
                if co > 10:
                    break
                print("waiting for : ", mesasage)
                time.sleep(wait)
                if type == 2 and co == 1:
                    self.refresh()
        if element == False:

            print("element not find : ", mesasage)
            if type == 2:
                mesasage = mesasage + self.check_error(valu)
            self.account.post_error(self.account_id, message=mesasage)
            self.exit()
        return element

    def get_screenshot(self, filename):

        try:
            self.driver.save_screenshot(r''+filename)

        except:
            time.sleep(1)
            print("get_screenshot")


    def get_url(self, url):
        try:
            self.driver.get(url)
        except:
            self.exit()
            print("get url", url)

 

 

  
    def refresh(self):
        try:
            self.driver.refresh()
        except:
            print('refresh')

        return self.driver.title

 
    def current_url(self):
        return self.driver.current_url

    def wait(self, x):

        try:
            wait = WebDriverWait(self.driver, 30)
            return wait.until(EC.presence_of_all_elements_located((By.XPATH, x)))
        except:
            self.exit()
            print("wait")


