from email.policy import default
import imp
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
from ps_lib.accounts import accounts
import json
import requests
import os
import time
from ps_lib.ps_str import ps_str
from ps_lib.proxy import ps_proxy
from ps_lib.timezone import t
from ps_lib.userAgent import l
from sys import exit
import sys
if sys.platform in ['Windows', 'win32', 'cygwin']:
    import pyautogui
import zipfile
import warnings
import random
import string


class browser:
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
        self.options = webdriver.ChromeOptions()
        # https://peter.sh/experiments/chromium-command-line-switches/
        ####################proxy user##############
        self.PROXY_PASS = False  # password
        if self.use_proxy:
            self.PROXY_USER = False  # username
            self.PROXY_PASS = False  # password
            self.PROXY_HOST = False
            self.PROXY_PORT = False
            self.PROXY_TYPE = 'PROXY'

            # ............Normal rotating proxy......................
        if self.proxy():

            print("done: proxy set")
            if self.use_proxy:
                # self.proxy_auth_plugin()
                self.proxy_auth_plugin_pac_script()
            else:
                self.PROXY_PASS = False

        if sys.platform in ['Windows', 'win32', 'cygwin']:
            driverUrl = 'chromedriver.exe'
        else:
            driverUrl = '/usr/bin/chromedriver'

        self.a = random.choice(l)

        self.options.add_argument(f'user-agent={self.a}')
        print('user set')

        if sys.platform not in ['Windows', 'win32', 'cygwin']:

            self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-infobars")
        self.options.add_argument("start-maximized")
        self.options.add_experimental_option("useAutomationExtension", False)
        self.options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        if headless:
            self.options.add_argument('--headless')
            self.options.add_argument('--disable-gpu')

        # self.options.add_argument("--lang=it-IT")
        self.options.add_argument("--no-sandbox")
        if profile_dir:
            self.options.add_argument("--user-data-dir={}".format(profile_dir))

        else:
            self.options.add_argument("--use-temporary-user-data-dir")

        self.driver = webdriver.Chrome(driverUrl, chrome_options=self.options)

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

    def proxy(self):
        try:

            proxyinfo = self.account.get_proxy_list()
            #............. check for use defaultProxy.............#
            dProxy = proxyinfo['defaultProxy']

            if type(dProxy) is dict:

                defaultProxy = ps_proxy(
                    company=dProxy['company'], key=dProxy['user'])
                defaultByCity = defaultProxy.firstProxy(
                    location=self.pva['extra'], proxyinfo=dProxy)

                if 'checkinfo' in defaultByCity:

                    self.proxy_save(px=dProxy, p=defaultByCity['checkinfo'])
                    self.PROXY_HOST = defaultByCity['host']
                    self.PROXY_PORT = defaultByCity['port']
                    self.PROXY_USER = defaultByCity['user']
                    self.PROXY_PASS = defaultByCity['password']
                    self.proxy_company = dProxy['company']
                    return True
                else:

                    self.account.post_log(id=self.pva['id'], messasge='city not present default {extra}'.format(
                        extra=self.pva['extra']))
                    print('city not present')
            #............. check for use backupProxy.............#
            bProxy = proxyinfo['backupProxy']

            if type(bProxy) is dict:
                backupProxy = ps_proxy(
                    company=bProxy['company'], key=bProxy['user'])
                backupByCity = backupProxy.backupProxy(
                    location=self.pva['extra'], proxyinfo=bProxy)

                if 'checkinfo' in backupByCity:

                    self.proxy_save(px=dProxy, p=backupByCity['checkinfo'])
                    self.PROXY_HOST = backupByCity['host']
                    self.PROXY_PORT = backupByCity['port']
                    self.PROXY_USER = backupByCity['user']
                    self.PROXY_PASS = backupByCity['password']
                    self.proxy_company = bProxy['company']
                    return True
                else:

                    self.account.post_log(id=self.pva['id'], messasge='city not present backup {extra}'.format(
                        extra=self.pva['extra']))
                    print('city not present')
            aProxy = proxyinfo['activeProxys']
            if type(aProxy) is dict:
                activeProxys = ps_proxy(
                    company=aProxy['company'], key=aProxy['user'])
                activeByCity = activeProxys.normalProxy(
                    location=self.pva['extra'], proxyinfo=aProxy)

                if 'checkinfo' in activeByCity:

                    self.proxy_save(px=dProxy, p=activeByCity['checkinfo'])
                    self.PROXY_HOST = activeByCity['host']
                    self.PROXY_PORT = activeByCity['port']
                    self.PROXY_USER = activeByCity['user']
                    self.PROXY_PASS = activeByCity['password']
                    self.proxy_company = aProxy['company']
                    return True
                else:

                    self.account.post_log(id=self.pva['id'], messasge='city not present normal {extra}'.format(
                        extra=self.pva['extra']))
                    print('city not present')
            else:
                self.use_proxy = False

            # ............packetstream.io......................

            # if self.proxy_company == "packetstream":
            #     self.PROXY_HOST = "proxy.packetstream.io"
            #     self.PROXY_PORT = 31112
            #     proxy = "%s:%s" % (self.PROXY_HOST, self.PROXY_PORT)
            # ............https://dashboard.soax.com/......................
            # if self.proxy_company == "soax":

            #     psproxy = ps_proxy(company="soax", key=self.PROXY_USER)
            #     soax = psproxy.proxysoax(self.PROXY_PASS)
            #     if soax:

            #         self.PROXY_USER = soax['login']
            #         self.PROXY_PASS = soax['password']
            #         self.PROXY_HOST = soax['ip']
            #         self.PROXY_PORT = soax['port']
            #         proxy = "%s:%s" % (self.PROXY_HOST, self.PROXY_PORT)
            #     else:
            #         self.PROXY_PASS = False
            #         proxy = "%s:%s" % ("proxy.soax.com", 9000)

            # ............rsocks.net......................
            # if self.proxy_company == "rsocks":

            #     headers = {
            #         'X-Auth-ID': '107841',
            #         'X-Auth-Key': '3a8390f63fa54c014a9bbaf2a0cdcbd4439f09f6217cbd04de59459f0e035eec'
            #     }
            #     resp = requests.post(
            #         'https://rsocks.net/api/v1/file/get-proxy', headers=headers, timeout=1)

            #     data = json.loads(resp.text)

            #     # data = random.choice(data['packages'])
            #     print(data['packages'])
            #     # proxy = rendomip=random.choice(data['ips'])
            #     data = data['packages'][self.packages_id]['ips']

            #     proxy = rendomip = random.choice(data)
                # ............proxyhorse.com......................

            # if self.proxy_company == "proxyhorse":

            #     psproxy = ps_proxy(company="proxyhorse",
            #                        key=self.PROXY_USER)

            #     pva_id = None
            #     if self.other_city == None:
            #         pva_id = self.account_id
            #     proxy = psproxy.proxyhorse(
            #         location=self.PROXY_PASS, pva_id=pva_id)
            #     self.PROXY_PASS = False

            #     if proxy:

            #         self.PROXY_HOST = proxy['ip']
            #         self.PROXY_PORT = proxy['port']
            #         self.PROXY_USER = proxy['login']
            #         self.PROXY_PASS = proxy['password']
            #     proxy = "%s:%s" % (self.PROXY_HOST, self.PROXY_PORT)

                # .............proxyrotator.com................

            # if self.proxy_company == "proxyrotator":
            #     url = 'http://falcon.proxyrotator.com:51337'
            #     params = dict(
            #         apiKey='TX2DLoKZVd6peF8fuJ59wqsyQgc4CGnv',
            #         userAgent='true',
            #         country=self.proxy_country,
            #         get='true',
            #         connectionType='Residential'
            #     )
            #     resp = requests.get(url, params=params, timeout=3)

            #     data = json.loads(resp.text)
            #     proxy = data['proxy']

                # .............pubproxy.com......................
                # url = 'http://pubproxy.com/api/proxy?&format=json&https=true&type=https&contry=IT'

        except (requests.ConnectionError, requests.Timeout) as exception:
            print('plz check your internet connection')

        return False

    def proxy_check(self, data):

        try:

            if self.proxy_company == "packetstream":
                data = self.PROXY_USER+":"+self.PROXY_PASS+"@"+data
                proxie = {"http": 'http://'+data, "https": 'http://'+data}

            if self.proxy_company == "soax":
                data = self.PROXY_USER+":"+self.PROXY_PASS+"@"+data
                proxie = {"http": "http://"+data, "https": "http://"+data}

            if self.proxy_company == "proxyhorse":
                data = self.PROXY_USER+":"+self.PROXY_PASS+"@"+data
                proxie = {"http": "http://"+data, "https": "http://"+data}

            url = "http://ip-api.com/json"
            timeout = 10
            r = requests.get(url, timeout=timeout, proxies=proxie)
            # print(r.text)

            if "isp" not in r.text and self.proxy_company == "soax":

                print(
                    "you can contract in your proxy company using this text : ", r.text)
                time.sleep(60)
                return False

            if self.proxy_save(data, json.loads(r.text)):

                return True
            else:
                return False

        except (requests.ConnectionError, requests.Timeout,) as exception:
            print('proxy error', exception)
            time.sleep(5)
            return False

    def get_ipinfo(self):

        try:

            url = "http://ip-api.com/json"
            timeout = 10
            r = requests.get(url, timeout=timeout)

            if "zip" in r.text:
                ip = json.loads(r.text)
            return ip['zip']

        except (requests.ConnectionError, requests.Timeout,) as exception:
            return 2200

    def proxy_save(self, px=None, p=None):
        try:
            print(px)

            self.proxy_city = p["city"]
            self.proxy_region = p['regionName']
            self.proxy_zip = p['zip']
            self.proxy_timezone = p['timezone']
            self.proxy_latLon = str(p['lat'])+":"+str(p["lon"])
            self.proxy_isp = p['isp']
            self.proxy_ip = p['query']
            if px['company'] == 'dichvusocks':
                self.PROXY_TYPE = 'SOCKS5'
            self.settimezoone(p)

            return True
        except Exception as e:
            print(e)
            print('proxy error')

            return False

    def ipinfo_save(self, software_name):
        try:

            message = ('%s-%s-%s-%s-%s-%s' % (software_name,
                                              self.proxy_ip,
                                              self.proxy_city,
                                              self.proxy_region,
                                              self.proxy_isp,
                                              self.proxy_company))
            self.account.post_log(id=self.pva['id'], messasge=message)

            return True
        except Exception as e:
            print(e)
            print('proxy error')

            return False

    def textProxy(self):
        return "{}:{}:{}".format(self.proxy_city, self.proxy_isp, self.proxy_ip)

    def settimezoone(self, p):
        oldTime = time.strftime('%X %x %Z')
        if sys.platform not in ['Windows', 'win32', 'cygwin']:

            os.environ['TZ'] = p["timezone"]
            time.tzset()

        if sys.platform in ['Windows', 'win32', 'cygwin']:
            for ti in t:
                if self.proxy_timezone in ti['utc']:
                    # os.system("tzutil /s \"{}\"".format(ti['value']))
                    pass
        newTime = time.strftime('%X %x %Z')
        print('old time: ', oldTime, "new time: ",
              newTime, 'timezone: ', p["timezone"])

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

    def try_select_element(self, selector):
        try:
            element = self.driver.find_element_by_css_selector(selector)
            if element.is_displayed() and element.is_enabled():
                # print('try_select_element')
                pass

        except:
            element = False

        return element

    def select_elements(self, selector):

        return self.driver.find_elements_by_css_selector(selector)

    def select_element_xpath(self, selector, mesasage="genarl work", type=1, valu=None, wait=1):
        # print(self.current_url())
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

    def upload_multiple(self, element, profile_id):
        try:
            sleep_time = 5

            imge_dir = os.getcwd() + "\img\{}".format(profile_id)
            if os.path.exists(imge_dir):
                for i in os.listdir(imge_dir):
                    if i.find('.') > 1:
                        element.click()
                        time.sleep(4)
                        # path of File
                        pyautogui.write(r""+imge_dir+"\{}".format(i))
                        pyautogui.press('enter')
                        sleep_time += 5
                        time.sleep(10)
            else:
                for i in os.listdir(os.getcwd() + "\img"):
                    if i.find('.') > 1:
                        element.click()
                        time.sleep(4)
                        pyautogui.write(r""+os.getcwd() + "\img\{}".format(i))
                        pyautogui.press('enter')
                        sleep_time += 5
                        time.sleep(10)
        except OSError:
            pass
        return sleep_time

    def try_xpath(self, selector, mesasage="genarl work"):
        try:
            element = self.driver.find_element_by_xpath(selector)
            if element.is_displayed() and element.is_enabled():
                element = True

        except:
            element = False

        return element

    def check_error(self, valu):
        m = "not"
        try:
            # check image upload page
            if "post-insert-images" not in self.current_url():
                m = "captcha key error and you need to report"
                self.captcha_bad(valu)
            # check proxy good or not
            proxydata = self.PROXY_HOST+':'+self.PROXY_PORT
            if self.proxy_check(proxydata) == False:
                m = "proxy error"
                self.captcha_good(valu)

        except Exception as e:
            pass

        return m

    def select_dropdown(self, parent, child):
        while True:
            try:
                dropdown = Select(
                    self.driver.find_element_by_css_selector(parent))

                break
            except:
                time.sleep(1)
                print("waiting for select_dropdown")
        dropdown.select_by_value(child)
        print("select_dropdown")
        return True

    def select_dropdown_text(self, parent, child):
        while True:
            try:
                dropdown = Select(self.driver.find_element_by_name(parent))

                break
            except:
                time.sleep(1)
                print("waiting for select_dropdown")
        dropdown.select_by_visible_text(child)
        print("select_dropdown")
        return True

    def slow_type(el, text):
        """Send a text to an element one character at a time with a delay."""
        print('body text typing')
        for character in text:
            el.send_keys(character)
            time.sleep(0.2)
        print('body text typing done')

    def get_screenshot(self, filename):

        try:
            self.driver.save_screenshot(r''+filename)

        except:
            time.sleep(1)
            print("get_screenshot")

    def captcha_bad(self, id):
        try:
            data = requests.get(
                "http://2captcha.com/res.php?key=4191a9a8a00ad6ce300a49d8d36935da&action=reportbad&id={1}".format(id))
        except:
            pass

    def captcha_good(self, id):
        try:
            data = requests.get(
                "http://2captcha.com/res.php?key=4191a9a8a00ad6ce300a49d8d36935da&action=reportgood&id={1}".format(id))
        except:
            pass

    def get_url(self, url):
        try:
            self.driver.get(url)
        except:
            self.exit()
            print("get url", url)

    def page_source(self):
        try:
            print('page_source')
            return self.driver.page_source.encode('utf-8')

        except:
            print('page_source')

    def get_title(self):
        try:
            self.driver.title
        except:
            self.exit()
            print("get_title")

        return self.driver.title

    def iframe(self, i):
        try:
            self.driver.switch_to.frame(i)
        except:
            print('switch frame')

    def switch_back(self):
        try:
            self.driver.switch_to.parent_frame()
        except:
            print('switch_back')

        return self.driver.title

    def refresh(self):
        try:
            self.driver.refresh()
        except:
            print('refresh')

        return self.driver.title

    def ps_message_box(self, account, chat_id, name):
        # try:
        # messenge_box = driver.find_element_by_tag_name('textarea')
        messenge_box = self.driver.find_element_by_css_selector(
            '[placeholder = "Your message"]')

        # messenge_box = driver.find_elements_by_css_selector('[placeholder = "Your message"]')
        messenge_box.click()
        for character in account.get_messsage(chat_id, name):
            messenge_box.send_keys(character)
            time.sleep(0.1)

        time.sleep(2)
        send_buton = self.driver.find_element_by_css_selector(
            '[ng-click="sendMessage()"]')
        send_buton.click()
        time.sleep(5)
        # except:
        print('eroor in: [ng-click="openChatDialog()"]')

    def scroll_element_into_view(self, element):
        """Scroll element into view"""
        y = element.location['y']-200

        s = "window.scrollTo(0,{})".format(y)
        self.driver.execute_script(s)

    def scroll_like_user(self, element):

        total_height = int(self.driver.execute_script(
            "return document.body.scrollHeight"))
        total = total_height / random.choice([2, 3, 4, 7, 1])

        for i in range(1, round(total), 1):
            self.driver.execute_script("window.scrollTo(0, {});".format(i))
            # time.sleep(1)
        self.scroll_element_into_view(element)

    def element_window_size(self, element):

        y = element.location['y']
        self.driver.set_window_size(800, y)

    def FindElementById(self, Element):
        wait = WebDriverWait(self.driver, 10)
        clickable = wait.until(EC.element_to_be_clickable((By.ID, Element)))
        return clickable

    def current_url(self):
        return self.driver.current_url

    def wait(self, x):

        try:
            wait = WebDriverWait(self.driver, 30)
            return wait.until(EC.presence_of_all_elements_located((By.XPATH, x)))
        except:
            self.exit()
            print("wait")

    def wait_css(self, x):

        try:
            print('wait css')
            wait = WebDriverWait(self.driver, 30)
            return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, x)))

        except:

            print("wait")
        return False

    def link_save(self, link):
        with open('links.txt', 'a') as file:
            file.write(link+"\n")

    def script_run(self, script, message='defult script'):
        try:

            done = self.driver.execute_script(script)
            print('done: ', message)
        except Exception as e:
            if "page" in message:
                message = message + str(self.page_source())
            self.account.post_error(self.account_id, message=message)
            self.exit()
            print('error: ', message, e)

    # proxy plugin

    def proxy_auth_plugin(self):

        manifest_json = """
		{
			"version": "1.0.0",
			"manifest_version": 2,
			"name": "Chrome Proxy",
			"permissions": [
				"proxy",
				"tabs",
				"unlimitedStorage",
				"storage",
				"<all_urls>",
				"webRequest",
				"webRequestBlocking"
			],
			"background": {
				"scripts": ["background.js"]
			},
			"minimum_chrome_version":"22.0.0"
		}
		"""

        background_js = """
		var config = {
				mode: "fixed_servers",
				rules: {
				singleProxy: {
					scheme: "%s",
					host: "%s",
					port: parseInt(%s)
				},
				bypassList: ["localhost"]
				}
			};

		chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

		function callbackFn(details) {
			return {
				authCredentials: {
					username: "%s",
					password: "%s"
				}
			};
		}

		chrome.webRequest.onAuthRequired.addListener(
					callbackFn,
					{urls: ["<all_urls>"]},
					['blocking']
		);
		""" % (self.PROXY_TYPE, self.PROXY_HOST, self.PROXY_PORT, self.PROXY_USER, self.PROXY_PASS)
        pluginfile = 'proxy_auth_plugin.zip'
        zp = zipfile.ZipFile(pluginfile, 'w')
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
        self.options.add_extension(pluginfile)

    def proxy_auth_plugin_pac_script(self):

        rules_json = """[
			{
				"id": 1,
				"priority": 1,
				"action": { "type": "block" },
				"condition": {"urlFilter": "jpeg", "resourceTypes": ["image"] }
			},
			{
				"id": 2,
				"priority": 2,
				"action": { "type": "block" },
				"condition": {"urlFilter": "jpg", "resourceTypes": ["image"] }
			},
			{
				"id": 3,
				"priority": 3,
				"action": { "type": "block" },
				"condition": {"urlFilter": "png)", "resourceTypes": ["image"] }
			}
		]"""
        block_rules_json = """[
			{
				"id": 1,
				"priority": 1,
				"action": { "type": "block" },
				"condition": {"urlFilter": "avif", "resourceTypes": ["image"] }
			}
		]"""
        manifest_json = """
		{
			"version": "1.0.0",
			"manifest_version": 2,
			"name": "Chrome Proxy",
			"declarative_net_request": {
				"rule_resources": [{
				"id": "ruleset_1",
				"enabled": true,
				"path": "rules.json"
				}]
			},
			"permissions": [
				"proxy",
				"tabs",
				"unlimitedStorage",
				"storage",
				"<all_urls>",
				"webRequest",
				"webRequestBlocking",
				"declarativeNetRequest"
			],
			"background": {
				"scripts": ["background.js"]
			},
			"minimum_chrome_version":"22.0.0"
		}
		"""

        background_js = """
		function FindProxyForURL(url, host) {
			if (url.search("GTM")>"1" ||
			url.search("google")>"1" ||
			url.search("GTM")>"1" ||
			url.search("GTM")>"1") {
				return 'DIRECT';

			}

			return "%s %s:%s";
			}
		var config = {
		mode: "pac_script",
		pacScript: {
			data:FindProxyForURL.toString(),
    		mandatory: true
			}
		};

		chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

		function callbackFn(details) {
			return {
				authCredentials: {
					username: "%s",
					password: "%s"
				}
			};
		}

		chrome.webRequest.onAuthRequired.addListener(
					callbackFn,
					{urls: ["<all_urls>"]},
					['blocking']
		);
		""" % (self.PROXY_TYPE, self.PROXY_HOST, self.PROXY_PORT, self.PROXY_USER, self.PROXY_PASS)
        pluginfile = 'proxy_auth_plugin.zip'
        zp = zipfile.ZipFile(pluginfile, 'w')
        if self.image_bock:
            zp.writestr("rules.json", rules_json)
        else:
            zp.writestr("rules.json", block_rules_json)

        zp.writestr("manifest.json", manifest_json)

        zp.writestr("background.js", background_js)
        self.options.add_extension(pluginfile)
