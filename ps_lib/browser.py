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
import time
from sys import exit
import warnings
import random
class browser:
	account_id=None


	def __init__(self,pofileLocation):
		self.account_id=pofileLocation
		#warnings.filterwarnings('ignore')
		self.PROXY = str(self.proxy())
		#......................Firefox..............................

		
		# firefox_capabilities = webdriver.DesiredCapabilities.FIREFOX
		# firefox_capabilities['marionette'] = True
		
		# firefox_capabilities['proxy'] = {
		# 	"proxyType": "MANUAL",
		# 	"httpProxy": self.PROXY,
		# 	# "ftpProxy": self.PROXY,
		# 	"sslProxy": self.PROXY
		# }
		# self.driver = webdriver.Firefox(capabilities=firefox_capabilities)

		#......................Chrome..............................


		prox = Proxy()
		prox.proxy_type = ProxyType.MANUAL
		prox.http_proxy = self.PROXY
		# # prox.socks_proxy = self.PROXY
		prox.ssl_proxy = self.PROXY
		Chrome_capabilities = webdriver.DesiredCapabilities.CHROME
		prox.add_to_capabilities(Chrome_capabilities)


		driverUrl = 'chromedriver.exe'
		options = webdriver.ChromeOptions()
		# options.add_argument('--proxy-server=http://%s' %self.PROXY )
		# options.add_argument("--no-sandbox")
		# options.add_argument("--disable-setuid-sandbox")
		# options.add_argument("--remote-debugging-port=9222")
		# options.add_argument("--disable-dev-shm-using")
		# options.add_argument("--disable-extensions")
		# options.add_argument("--disable-gpu")
		# options.add_argument("start-maximized")
		# options.add_argument("disable-infobars")
		# options.add_argument("--headless")
		# options.add_argument("--no-sandbox")
		# options.add_argument("--disable-dev-shm-usage")
		options.add_argument("user-data-dir=profiles\\"+pofileLocation)
		self.driver = webdriver.Chrome(driverUrl,chrome_options=options,desired_capabilities=Chrome_capabilities)
		
		# self.driver = webdriver.PhantomJS(service_args=service_args)

	def exit(self):
		self.driver.quit()
	def proxy(self):
		while True:
			try:
				url = 'http://falcon.proxyrotator.com:51337'
				# url = 'http://falcon.proxyrotator.com:51337'
				# url = 'http://pubproxy.com/api/proxy?&format=json&https=true&type=https&contry=IT'

				params = dict(
					apiKey='de2nf8XPYyUJscFmwj6Z9DoEBkNgQGKb',
					userAgent='true',
					country='IT',
					get = 'true',
					connectionType='Residential'
				)
				headers={
					'X-Auth-ID':'107841',
					'X-Auth-Key':'3a8390f63fa54c014a9bbaf2a0cdcbd4439f09f6217cbd04de59459f0e035eec'
				}
				# resp = requests.get(url, timeout=3)
				resp = requests.post('https://rsocks.net/api/v1/file/get-proxy', params=params, headers=headers,timeout=1)
				# data = resp.json
				data = json.loads(resp.text)
				data = data['packages']['257646']['ips']
				print(data)
				
			except (requests.ConnectionError, requests.Timeout) as exception:
				print('plz check your internet connection')
				continue

			
			rendomip=random.choice(data)
			print(rendomip)
			if self.proxy_check(rendomip):
				break
			

			
		# return data['ipPort']
		# return data['proxy']
		return rendomip
	def proxy_check(self,data):
		
		
		try:
			
			proxies = {
				
				# "http": 'http://'+data['proxy'],
				"http": 'http://'+data,
				"https": 'http://'+data,
				# "https": 'http://'+data['ipPort']
				}
				
			url = "http://api.myip.com"
			timeout = 10
			request = requests.get(url, timeout=timeout,proxies=proxies)
			print(request.text)
			return True
		except (requests.ConnectionError, requests.Timeout,) as exception:
			print('proxy error' ,exception)
			time.sleep(5)
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
				if co >100:
					break
				print("waiting for ",selector)
				# self.driver.implicitly_wait(1)
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
				if co > 60:
					break
				print("waiting for ",selector)
				time.sleep(1)
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
			return self.driver.page_source.encode('utf-8')
			print('page_source')
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
