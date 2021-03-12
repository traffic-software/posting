from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from selenium import webdriver
import time
import warnings
class browser:
	def __init__(self,pofileLocation):

		#warnings.filterwarnings('ignore')
		self.service_args = [
				'--proxy=http://127.0.0.1:23321',
				#'--proxy-auth=USER:PWD',
				'--proxy-type=socks5',
				]
		driverUrl = 'chromedriver.exe'
		options = webdriver.ChromeOptions()
		# chromeOptions.add_argument("--no-sandbox")
		# chromeOptions.add_argument("--disable-setuid-sandbox")
		# options.add_argument("--remote-debugging-port=9222")
		# chromeOptions.add_argument("--disable-dev-shm-using")
		# chromeOptions.add_argument("--disable-extensions")
		# chromeOptions.add_argument("--disable-gpu")
		# chromeOptions.add_argument("start-maximized")
		# chromeOptions.add_argument("disable-infobars")
		# options.add_argument("--headless")
		# options.add_argument("--no-sandbox")
		# options.add_argument("--disable-dev-shm-usage")
		options.add_argument("user-data-dir=profiles\\"+pofileLocation)
		self.driver = webdriver.Chrome(driverUrl,chrome_options=options)
		# self.driver = webdriver.PhantomJS(service_args=service_args)

	def exit(self):
		self.driver.quit()

	def select_element(self,selector):
		while True:
			try:
				element = self.driver.find_element_by_css_selector(selector)
				if element.is_displayed():
					print("element ", selector)
					break
			except:
				time.sleep(1)
				print("waiting for ",selector)
		return element
	def select_element_xpath(self,selector):

		while True:
			try:
				element = self.driver.find_element_by_xpath(selector)
				if element.is_displayed() and element.is_enabled():
					print("element ", selector)
					break
			except:
				time.sleep(1)
				print("waiting for ",selector)
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
		print(y)
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
