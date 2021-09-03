from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
from ps_lib.accounts import accounts
import json, requests
import os, time
from fake_useragent import UserAgent
import time
from sys import exit
import os
import sys
import zipfile
import warnings
import random
import string
class browser:
	account_id=None


	def __init__(self,pofileLocation,packages_id,use_proxy=True,proxy_company='proxyrotator',proxy_country="IT",proxy_user='malaknoyn100',proxy_pass="51310fe4"):
		
		self.proxy_country = proxy_country
		self.proxy_city = None
		self.proxy_region = None
		self.proxy_zip = None
		self.proxy_timezone = None
		self.proxy_latLon = None
		self.proxy_isp = None
		self.proxy_ip = None
		self.proxy_company = proxy_company
		self.account_id=pofileLocation
		warnings.filterwarnings('ignore')
		#................account.....................................
		self.account = accounts()
		#......................Chrome..............................
		self.options = webdriver.ChromeOptions()
		#https://peter.sh/experiments/chromium-command-line-switches/
		####################proxy user##############
		self.use_proxy =use_proxy
		if packages_id == 'no':
			self.use_proxy =False
		if self.use_proxy:
			self.packages_id = packages_id
			self.PROXY_USER = proxy_user # username
			self.PROXY_PASS = proxy_pass # password
			
			
			#............Normal rotating proxy......................
			self.PROXY = str(self.proxy())
			proxy = self.PROXY.split(":")
			self.PROXY_HOST =  proxy[0]
			self.PROXY_PORT =  proxy[1]
			self.PROXY_TYPE = 'http'
			
			
			
			# self.proxy_auth_plugin()
			self.proxy_auth_plugin_pac_script()

		
		if sys.platform in ['Windows', 'win32', 'cygwin']:
			driverUrl = 'chromedriver.exe'
		else:
			driverUrl = '/usr/bin/chromedriver'
			

		# ua = UserAgent(cache=False)
		# ua.update()
		# a = ua.safari
		
		# self.options.add_argument(f'user-agent={a}')

		
		if sys.platform not in ['Windows', 'win32', 'cygwin']:
			
			self.options.add_argument("start-maximized")
			self.options.add_argument("--disable-dev-shm-usage")
		self.options.add_argument("--disable-infobars")
			
		
		self.options.add_argument("--lang=it-IT")
		self.options.add_argument("--no-sandbox")
		
		self.options.add_argument("--use-temporary-user-data-dir")
		self.driver = webdriver.Chrome(driverUrl,chrome_options=self.options)
		
		

	def exit(self):

		self.driver.quit()
	def proxy(self):
		while True:
			try:
				if self.proxy_company =="packetstream":
					self.PROXY_HOST = "proxy.packetstream.io"
					self.PROXY_PORT = 31112
					# self.PROXY_USER = "malaknoyn"
					# self.PROXY_PASS = "4mdloQgXxS8lcB3J_country-%s_session-%s"% (self.proxy_country,''.join(random.choice(string.ascii_letters) for i in range(10)))
					proxy = "%s:%s"%(self.PROXY_HOST,self.PROXY_PORT)
				#............rsocks.net......................
				if self.proxy_company =="rsocks":
					
				
				
					headers={
						'X-Auth-ID':'107841',
						'X-Auth-Key':'3a8390f63fa54c014a9bbaf2a0cdcbd4439f09f6217cbd04de59459f0e035eec'
					}
					resp = requests.post('https://rsocks.net/api/v1/file/get-proxy', headers=headers,timeout=1)
					
					data = json.loads(resp.text)
					
					# data = random.choice(data['packages'])
					print(data['packages'])
					# proxy = rendomip=random.choice(data['ips'])
					data = data['packages'][self.packages_id]['ips']
					
					proxy = rendomip=random.choice(data)



				#.............proxyrotator.com................
				
				if self.proxy_company =="proxyrotator": 
					url = 'http://falcon.proxyrotator.com:51337'
					params = dict(
						apiKey='TX2DLoKZVd6peF8fuJ59wqsyQgc4CGnv',
						userAgent='true',
						country=self.proxy_country,
						get = 'true',
						connectionType='Residential'
					)
					resp = requests.get(url,params=params, timeout=3)
					
					data = json.loads(resp.text)
					proxy = data['proxy']



				#.............pubproxy.com......................
				# url = 'http://pubproxy.com/api/proxy?&format=json&https=true&type=https&contry=IT'
				
			except (requests.ConnectionError, requests.Timeout) as exception:
				print('plz check your internet connection')
				continue

			
			print(proxy)
			if self.proxy_check(proxy):
				break
		return proxy
	def proxy_check(self,data):
		
		
		try:
			
			if self.proxy_company =="packetstream":
				data  = self.PROXY_USER+":"+self.PROXY_PASS+"@"+data
			proxie = {"http": 'http://'+data,"https": 'http://'+data}
			
			
				
			url = "http://ip-api.com/json"
			timeout = 10
			r = requests.get(url, timeout=timeout,proxies=proxie)
			if self.proxy_save(data, json.loads(r.text)):
				
				return True
			else:
				return False
		
		except (requests.ConnectionError, requests.Timeout,) as exception:
			print('proxy error' ,exception)
			time.sleep(5)
			return False

	def proxy_save(self,px,p):
		
		

		
		try:
			
			self.proxy_city = p["city"]
			self.proxy_region = p['regionName']
			self.proxy_zip = p['zip']
			self.proxy_timezone = p['timezone']
			self.proxy_latLon = str(p['lat'])+":"+str(p["lon"])
			self.proxy_isp = p['isp']
			self.proxy_ip = p['query']
			
			if sys.platform not in ['Windows', 'win32', 'cygwin']:
				self.proxy_city = p["city"]
				oldTime = time.strftime('%X %x %Z')
				
				os.environ['TZ'] = p["timezone"]
				time.tzset()
				newTime = time.strftime('%X %x %Z')
				print('old time: ',oldTime,"new time: ",newTime,'timezone: ',p["timezone"])
			
			return True
		except :
			print('proxy error')
			
			return False

        
        

	def select_element(self,selector):
		co=0
		element=False
		while True:
			try:
				element = self.driver.find_element_by_css_selector(selector)
				if element.is_displayed():
					print("element ", selector)
					break
			except:
				co = co+1
				if co >10:
					break
				print("waiting for ",selector)
				self.driver.implicitly_wait(1)
		if element == False:
			print("element not find: ",selector)
			
			self.account.account_inactive(self.account_id)
			self.exit()
			exit()
		return element
	def select_element_xpath(self,selector,mesasage="genarl work"):
		co = 0
		element = False
		while True:
			try:
				element = self.driver.find_element_by_xpath(selector)
				if element.is_displayed() and element.is_enabled():
					print("done : ",mesasage)
					break
			except:
				co = co + 1
				if co > 10:
					break
				print("waiting for : ",mesasage)
				self.driver.implicitly_wait(1)
		if element == False:
			
			print("element not find : ",mesasage)
			if "Check your proxy" in str(self.page_source()):
				mesasage = mesasage + " proxy error"
			self.account.post_error(self.account_id,message=mesasage)
			self.account.account_inactive(self.account_id)
			self.exit()
			exit()
		return element
	
	def select_dropdown(self,parent,child):
		while True:
			try:
				dropdown = Select(self.driver.find_element_by_css_selector(parent))



				break
			except:
				time.sleep(1)
				print("waiting for select_dropdown")
		dropdown.select_by_value(child)
		print("select_dropdown")
		return True
	def select_dropdown_text(self,parent,child):
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
	def get_screenshot(self,filename):

			try:
				self.driver.save_screenshot(r''+filename)

			except:
				time.sleep(1)
				print("get_screenshot")

	def get_url(self,url):
		try:
			self.driver.get(url)
		except:
			self.exit()
			print("get url", url)
		return self.driver.title
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
	def iframe(self,i):
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
	def ps_message_box(self,account, chat_id, name):
		# try:
		# messenge_box = driver.find_element_by_tag_name('textarea')
		messenge_box = self.driver.find_element_by_css_selector('[placeholder = "Your message"]')

		# messenge_box = driver.find_elements_by_css_selector('[placeholder = "Your message"]')
		messenge_box.click()
		for character in account.get_messsage(chat_id, name):
			messenge_box.send_keys(character)
			time.sleep(0.1)

		time.sleep(2)
		send_buton = self.driver.find_element_by_css_selector('[ng-click="sendMessage()"]')
		send_buton.click()
		time.sleep(5)
		# except:
		print('eroor in: [ng-click="openChatDialog()"]')

	def	scroll_element_into_view(self,element):
		"""Scroll element into view"""
		y = element.location['y']-200

		s = "window.scrollTo(0,{})".format(y)
		self.driver.execute_script(s)

	def element_window_size(self, element):

		y = element.location['y']
		self.driver.set_window_size(800, y)

	def FindElementById(self,Element):
		wait = WebDriverWait(self.driver, 10)
		clickable = wait.until(EC.element_to_be_clickable((By.ID, Element)))
		return clickable

	def current_url(self):
		return self.driver.current_url
	def link_save(self,link):
		with open('links.txt', 'a') as file:
			file.write(link+"\n")
	def script_run(self,script,message='defult script'):
		try:
			
			done= self.driver.execute_script(script)
			print('done: ',message)
		except:
			if "page" in message:
				message = message + str(self.page_source())
			self.account.post_error(self.account_id,message=message)
			self.exit()
			print('error: ',message)
			exit()
		
		
	
	#proxy plugin 
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
		""" % (self.PROXY_TYPE,self.PROXY_HOST, self.PROXY_PORT, self.PROXY_USER, self.PROXY_PASS)
		pluginfile = 'proxy_auth_plugin.zip'
		zp=zipfile.ZipFile(pluginfile, 'w')
		zp.writestr("manifest.json", manifest_json)
		zp.writestr("background.js", background_js)
		self.options.add_extension(pluginfile)
	
	def proxy_auth_plugin_pac_script(self):


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
		function FindProxyForURL(url, host) {
			if (url.search("static")>"1" || 
			url.search("cloudflare")>"1" || 
			url.search("GTM")>"1" ||
			url.search("hsw.js")>"1") {
				return 'DIRECT';
				
			}
			
			return "PROXY %s:%s";
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
		""" % (self.PROXY_HOST, self.PROXY_PORT, self.PROXY_USER, self.PROXY_PASS)
		pluginfile = 'proxy_auth_plugin.zip'
		zp=zipfile.ZipFile(pluginfile, 'w')
		zp.writestr("manifest.json", manifest_json)
		zp.writestr("background.js", background_js)
		self.options.add_extension(pluginfile)
	
