from anticaptchaofficial.recaptchav2enterpriseproxyless import *
import requests
import time
from sys import exit
class capcha:

	anti_api='73644003524468b0603694eff6fb6e6f'
	tow_api=None
	type = None

	def __init__(self,anti_api_key='73644003524468b0603694eff6fb6e6f',tow_api_key=None,type=None,lan='en'):
		self.anti_api = anti_api_key
		self.tow_api = tow_api_key
		self.type = type
		self.lan = lan 


	# def anticaptcha(self,siteKe,pageUrl):
	# 	client = AnticaptchaClient(self.anti_api)
	# 	task = NoCaptchaTaskProxylessTask(pageUrl, siteKe)
	# 	job = client.createTask(task)
	# 	job.join()
	# 	print('recaptcha task done')
	# 	return job.get_solution_response()
	def recaptchaV2EnterpriseProxyless(self,siteKe,pageUrl):
		solver = recaptchaV2EnterpriseProxyless()
		solver.set_verbose(1)
		solver.set_key(self.anti_api)
		solver.set_website_url(pageUrl)
		solver.set_website_key(siteKe)
		g_response = solver.solve_and_return_solution()
		if g_response != 0:
			print("g-response: "+g_response)
		else:
			print("task finished with error "+solver.error_code)
	def two_captcha(self,siteKe,pageUrl,enterprise=0):
			id = self.two_start(siteKe,pageUrl,enterprise)
			response =self.two_respond(id)
			print('task done')
			return {"id":id,"key":response}

	def two_start(self,siteKe,pageUrl,enterprise=0):
		id=None

		try:
			if self.type == 1:
				data = requests.get("http://2captcha.com/in.php?lang={0}&key={1}&method=hcaptcha&sitekey={2}&pageurl={3}".format(self.lan,self.tow_api, siteKe, pageUrl))
			
			else:
				data = requests.get("http://2captcha.com/in.php?lang={0}&key={1}&method=userrecaptcha&googlekey={2}&pageurl={3}&enterprise={4}".format(self.lan,self.tow_api, siteKe, pageUrl,enterprise))
			data = data.text.split("|")
			id = data[1]
		except:
			print('captcha requests not work')
		return id
	def two_respond(self,id):
		text = None
		while True:
			time.sleep(10)
			data = requests.get("http://2captcha.com/res.php?key={0}&action=get&id={1}".format(self.tow_api,id))
			t = data.text
			print(t)
   
			if "|" in t:
				data =t.split("|")
				text=data[1]
				break
			else:
				print('CAPCHA_NOT_READY') 
		return text