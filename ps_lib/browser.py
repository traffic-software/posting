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
# from fake_useragent import UserAgent
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


	def __init__(self,pofileLocation,packages_id,use_proxy=True,proxy_company='proxyrotator',proxy_country="IT"):
		
		self.proxy_country = proxy_country
		self.proxy_company = proxy_company
		self.account_id=pofileLocation
		warnings.filterwarnings('ignore')
		#......................Chrome..............................
		self.options = webdriver.ChromeOptions()
		####################proxy user##############
		self.use_proxy =use_proxy
		if packages_id == 'no':
			self.use_proxy =False
		if self.use_proxy:
			self.packages_id = packages_id
			self.PROXY_USER = 'malaknoyn100' # username
			self.PROXY_PASS = '51310fe4' # password
			
			#............packetstream.io......................
			if self.proxy_company =="packetstream":
				self.PROXY_TYPE = 'http'
				self.PROXY_HOST = "proxy.packetstream.io"
				self.PROXY_PORT = 31112
				self.PROXY_USER = "malaknoyn"
				self.PROXY_PASS = "4mdloQgXxS8lcB3J_country-%s_session-%s"% (self.proxy_country,''.join(random.choice(string.ascii_letters) for i in range(10)))
			else:
				#............Normal rotating proxy......................
				self.PROXY = str(self.proxy())
				proxy = self.PROXY.split(":")
				self.PROXY_HOST =  proxy[0]
				self.PROXY_PORT =  proxy[1]
				self.PROXY_TYPE = 'http'
			
			
			
			self.proxy_auth_plugin()

		
		
		
		###################normal proxy use#########


		# prox = Proxy()
		# prox.proxy_type = ProxyType.MANUAL
		# prox.http_proxy = self.PROXY
		# # prox.socks_proxy = self.PROXY
		# prox.ssl_proxy = self.PROXY
		# Chrome_capabilities = webdriver.DesiredCapabilities.CHROME
		# prox.add_to_capabilities(Chrome_capabilities)


		
		if sys.platform in ['Windows', 'win32', 'cygwin']:
			driverUrl = 'chromedriver.exe'
		else:
			driverUrl = '/usr/bin/chromedriver'

		# ua = UserAgent(cache=False)
		# a = ua.safari
		
		# self.options.add_argument(f'user-agent={a}')

		# self.options.add_argument('--proxy-server=http://%s' %self.PROXY )
		# self.options.add_argument("--remote-debugging-port=9222")
		
		if sys.platform not in ['Windows', 'win32', 'cygwin']:
			self.options.add_argument("--headless")
			self.options.add_argument("--disable-gpu")
			self.options.add_argument("start-maximized")
			self.options.add_argument("--remote-debugging-port=9222")
			
		
		self.options.add_argument("--use-temporary-user-data-dir")
		# self.options.add_argument("--use-temporary-user-data-dir=profiles\\"+pofileLocation)
		self.driver = webdriver.Chrome(driverUrl,chrome_options=self.options)
		
		

	def exit(self):
		self.driver.quit()
	def proxy(self):
		while True:
			try:
				
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
					proxy
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
			
			proxies = {"http": 'http://'+data,"https": 'http://'+data}
				
			url = "http://api.myip.com"
			timeout = 10
			request = requests.get(url, timeout=timeout,proxies=proxies)
			if self.proxy_save(data, json.loads(request.text)):
				return True
			else:
				return False
		except (requests.ConnectionError, requests.Timeout,) as exception:
			print('proxy error' ,exception)
			time.sleep(5)
			return False
	def proxy_save(self,px,p):
		print(p)
		try:
			
			ip =p['ip']
			my_file = open('proxy.txt', 'a')
			data = str(px)+':'+str(ip)+"\n"
			my_file.write(data)
			my_file.close()
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
			account = accounts()
			account.account_inactive(self.account_id)
			self.exit()
			exit()
		return element
	def select_element_xpath(self,selector):
		co = 0
		element = False
		while True:
			try:
				element = self.driver.find_element_by_xpath(selector)
				if element.is_displayed() and element.is_enabled():
					print("element ", selector)
					break
			except:
				co = co + 1
				if co > 10:
					break
				print("waiting for ",selector)
				self.driver.implicitly_wait(1)
		if element == False:
			print("element not find: ",selector)
			account = accounts()
			account.account_inactive(self.account_id)
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
	def script_run(self,script):
		return self.driver.execute_script(script)
	def link_save(self,link):
		with open('links.txt', 'a') as file:
			file.write(link+"\n")
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
				bypassList: ["localhost","whatismyipaddress.com","*nr-data.net","*cloudflare.com","*newrelic.com","*google-analytics.com","*googletagmanager.com"]
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
		var config = {
		mode: "pac_script",
		pacScript: {
			data: "function FindProxyForURL(url, host) {\n" +
				"  shExpMatch(url, "https://www.google.com/search/*"))\n" +
				"    return 'PROXY %s:%s';\n" +
				"  return 'DIRECT';\n" +
				"}"
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
	
