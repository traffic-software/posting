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
from datetime import datetime
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
        if sys.platform in ['Windows', 'win32', 'cygwin']:
            driverUrl = 'chromedriver.exe'
        else:
            driverUrl = 'chromedriver'

        # self.options.arguments.extend(
        #     ["--no-sandbox", "--disable-setuid-sandbox"])
        # self.options.add_argument("start-maximized")

        self.driver = uc.Chrome(options=self.options, use_subprocess=True)
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

    def update_recovery(self, recovery_email, id):
        link = self.driver.current_url
        linkarg = link.split('?')
        recovery_link = "https://myaccount.google.com/recovery/email?" + \
            linkarg[1]
        try:
            self.driver.get(recovery_link)
            self.driver.implicitly_wait(5)
            input_recovery_clear = self.driver.find_element(
                By.XPATH, '(//input[@type="email"])').clear()
            self.driver.implicitly_wait(1)
            input_recovery = self.visibil_element(
                'xpath', '(//input[@type="email"])', 3)
            input_recovery.send_keys(recovery_email)
            self.driver.implicitly_wait(1)
            input_recovery_submit = self.driver.find_element(
                By.XPATH, '(//input[@type="email"])').send_keys(Keys.RETURN)
            self.driver.implicitly_wait(10)
            self.account.rec_mail(id, recovery_email)

            return True
        except:
            return False

    def change_password(self, new_pass, id):
        link = self.driver.current_url
        linkarg = link.split('?')
        pass_change = "https://myaccount.google.com/signinoptions/password?" + \
            linkarg[1]
        self.driver.get(pass_change)
        time.sleep(2)
        try:
            new_pass = self.account.ran_password()
            # print('try to chenge password:'+new_pass)
            input_pass_1 = self.driver.find_element(
                By.XPATH, '(//input[@type="password"])[1]')
            input_pass_1.send_keys(new_pass)
            input_pass_2 = self.visibil_element(
                'xpath',  '(//input[@type="password"])[2]', 3)
            input_pass_2.send_keys(new_pass)
            try:
                pass_submit = self.visibil_element(
                    'xpath', '//button[@type="submit"]', 3)
                pass_submit.click()
            except:
                pass_submit = self.visibil_element(
                    'xpath', '//button[@type="button"]', 3)
                pass_submit.click()
            self.driver.implicitly_wait(20)
            self.account.password_mail(id, new_pass)
            # connection = db()
            # cursor = connection.cursor()
            # cursor.execute(
            #     """UPDATE gmail SET password= '{0}' WHERE id='{1}';""".format(new_pass, id))
            # connection.commit()
            # connection.close()
            return True
        except Exception:
            return False

    def remove_number(self, id):  # done
        try:
            link = self.driver.current_url
            linkarg = link.split('?')
            recovery_link = "https://myaccount.google.com/phone?"+linkarg[1]
            self.driver.get(recovery_link)
            phonenumber = self.visibil_element(
                'xpath', ('//div[contains(@data-phone,"+") and @data-encrypted-phone]'), 10)

            if phonenumber:
                phonenumber.click()
                remove_number = self.visibil_element(
                    'xpath', ('(//*[@jsaction and @jscontroller and @data-idom-class])[3]'), 10)
                if remove_number:
                    remove_number.click()
                    remove_number_f = self.visibil_element(
                        'xpath', ('(//span[@class="CwaK9"]//child::span[@class="RveJvd snByac"])[4]'), 10)
                    if remove_number_f:
                        remove_number_f.click()
                        self.driver.implicitly_wait(10)
                return True
            else:
                print('don not have number')
                return False
        except Exception:
            return False

    def activity_login(self):
        self.get_url("https://myaccount.google.com/u/0/notifications")
        device_main = self.driver.find_elements(
            By.XPATH, '//div[@role = "main"]//child::li//child::a')
        links = []
        for x in device_main:
            link = (x.get_attribute("href"))
            links.append(link)
        for x in links:
            try:
                self.get_url(x)
                self.driver.implicitly_wait(5)
                self.driver.find_element(By.XPATH, "(//button)[6]").click()
                self.driver.implicitly_wait(5)
            except Exception:
                pass

    def find_time(self, id):
        mail = 'https://mail.google.com/mail/u/0/#all'
        self.get_url(mail)
        mail_time = False
        self.driver.implicitly_wait(25)
        try:
            table = self.driver.find_elements(
                By.XPATH, '(//div[@aria-label="Show more messages" ]//span)')
            parpage = int(table[3].text)-int(table[2].text)+1

            self.driver.get(
                'https://mail.google.com/mail/u/0/#all/p{0}'.format(round(int(table[4].text)/parpage)))

        except Exception:
            pass
        try:
            self.driver.implicitly_wait(10)

            # driver.refresh()
            table_time = self.driver.find_elements(
                By.XPATH, '//*[contains(@aria-label, ",")]')
            # print(len(table_time))
            mail_time = table_time[-1].get_attribute("aria-label")

            # print("OLD")
        except:
            print('not time')
        if mail_time:
            self.account.mail_data(id, mail_time)

        print("Time >> ", mail_time)

    def language_cng(self, id, email_pass):  # done
        try:
            link = self.driver.current_url
            linkarg = link.split('?')
            self.get_url("https://myaccount.google.com/language?"+linkarg[1])
            email = self.save_email(id, email_pass)

            self.driver.find_element(
                By.XPATH, '//span//parent::button[@aria-label]').click()
            time.sleep(0.5)
            self.driver.find_element(
                By.XPATH, '//span[text()="English"]//parent::span//parent::span//parent::li[@aria-label="English"]').click()
            self.driver.find_element(
                By.XPATH, '//span[text()="United States"]//parent::span//parent::span//parent::li[@aria-label="United States"]').click()
            time.sleep(0.5)
            self.driver.find_element(
                By.XPATH, '//button[@data-mdc-dialog-action="ok"]').click()
            time.sleep(2)
            return email
        except Exception:
            return False

    def req_change_password(self, id):
        link = self.driver.current_url
        if 'changepassword/changepasswordform' in link:
            try:
                new_pass = self.account.ran_password()
                print('direct password chenge :'+new_pass)
                input_pass_1 = self.driver.find_element(
                    By.XPATH, '(//input[@type="password"])[1]')
                input_pass_1.send_keys(new_pass)
                input_pass_2 = self.visibil_element(
                    'xpath',  '(//input[@type="password"])[2]', 3)
                input_pass_2.send_keys(new_pass)
                try:
                    pass_submit = self.visibil_element(
                        'xpath', '//button[@type="submit"]', 3)
                    pass_submit.click()
                except:
                    pass_submit = self.visibil_element(
                        'xpath', '//button[@type="button"]', 3)
                    pass_submit.click()
                self.driver.implicitly_wait(20)

                self.account.password_mail(id, new_pass)
                # connection = db()
                # cursor = connection.cursor()
                # cursor.execute(
                #     """UPDATE gmail SET password= '{0}' WHERE id='{1}';""".format(new_pass, id))
                # connection.commit()
                # connection.close()
                return True
            except Exception:
                return False
        else:
            return False

    def gmail_login(self, id):

        returndata = False

        active_url = self.current_url()

        if "disabled" in active_url:
            print('disabled')
            self.account.gmail_update(id=id, status=12)
        if "challenge/ootp" in active_url:
            print('challenge/ootp')
            self.account.gmail_update(id=id, status=14)

        if 'info/sessionexpired?' in active_url:
            print("signinrejecte")
            self.account.gmail_update(id=id, status=16)

        if 'signin/challenge/rn' in active_url:
            print("signinrejecte")
            self.account.gmail_update(id=id, status=16)
        if 'signinrejecte' in active_url:
            print("signinrejecte")
            self.account.gmail_update(id=id, status=16)
        if 'challenge/recaptcha' in active_url:
            print("challenge/recaptcha")
            self.account.gmail_update(id=id, status=19)

        if 'signin/rejected' in active_url:
            print('rejected')
            self.account.gmail_update(id=id, status=16)

        if 'challenge/dp' in active_url:
            print("challenge/dp")
            self.account.gmail_update(id=id, status=14)

        if 'challenge/pk/presend' in active_url:
            print("challenge/dp")
            self.account.gmail_update(id=id, status=14)

        if 'challenge/hpwd' in active_url:
            print("challenge/dp")
            self.account.gmail_update(id=id, status=14)

        if 'challenge/rn?' in active_url:
            print("challenge/dp")
            self.account.gmail_update(id=id, status=14)

        if "challenge/ipp" in active_url:
            print('bell')
            self.account.gmail_update(id=id, status=14)

        if 'signinchooser' in active_url:
            print('signinchooser')

        if 'unknownerror' in active_url:
            print('unknownerror')
            self.account.gmail_update(id=id, status=16)

        if 'challenge/selection' in active_url:
            print('challenge/selection')
            self.account.gmail_update(id=id, status=14)

        if 'challenge/iap' in active_url:
            self.account.gmail_update(id=id, status=14)

            print("challenge/iap")

        if 'speedbump/changepassword' in active_url:
            print("speedbump/changepassword")
            returndata = True

        if "changepassword/changepasswordform" in active_url:
            print("changepassword/changepasswordform")
            returndata = True

        if "signinoptions/rescuephone" in active_url:
            print("signinoptions/rescuephone")
            returndata = True

        self.driver.implicitly_wait(2)

        return returndata

    def device_activity(self):
        self.get_url("https://myaccount.google.com/device-activity")
        device_main = self.driver.find_elements(
            By.XPATH, "//a[contains(@href,'device-activity')]")

        links = []
        for x in device_main:
            link = (x.get_attribute("href"))
            if '.com/SignOutOptions' in link:
                continue

            links.append(link)

        for x in links:
            try:

                self.get_url(x)
                self.driver.implicitly_wait(5)
                logout = self.visibil_element(
                    'xpath', "//div[@role='presentation']//span[1]", 2)
                if logout:
                    logout.click()
                self.driver.implicitly_wait(3)
                dialog = self.driver.find_elements(
                    By.XPATH, "//span[contains(text(),'Sign out')]")
                dialog[-1].click()
            except Exception:
                pass

    def save_email(self, id, email_pass):
        # get hiden tag
        gettext = self.driver.execute_script(
            """return document.evaluate('//*[contains(text(),"@gmail.com")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")

        text = gettext.get_attribute("innerHTML")
        email = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)[0]
        self.account.newgmail(id, email)

    def rec_def(self, recovery_email):
        rec = ""
        print('recovery_email: {0}'.format(recovery_email))

        try:
            rec_final = self.driver.visibil_element(
                'xpath', '//ul//child::li[3]', 4)
            rec_final.click()
            rec = False
            rec_in = self.driver.visibil_element(
                'xpath',  '//input[@type ="email"]', 5)
            rec_in.send_keys(recovery_email)

            rec_in.send_keys(Keys.RETURN)
            rec = True
            rec_error = self.driver.visibil_element(
                'xpath', '//div[@class="o6cuMc Jj6Lae"]', 1)
            if rec_error:
                return 4

        except Exception:
            if rec == False:
                return 4

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
