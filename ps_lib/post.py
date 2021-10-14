import sqlite3
from sys import exit
import requests
import random
from ps_lib.ps_setup import table
class post:
	def __init__(self):
		self.software = table()

		self.conn = sqlite3.connect(self.software.databasesfile)
		self.bed=random.choice([1,2,3])
		self.bat=0
		self.price=3
		self.set_utility()
	def get_post(self):
		url = 'http://{host}/api/v1/post/new/{token}'.format(host=self.software.host_verify(),token=self.software.software_token())
		r = requests.get(url)

		if "error" in r.json():
			print("error",r.json()['message'])
			exit()
		return r.json()["data"]
	def set_utility(self):
		
		if self.bed==1:
			self.bat=1
			self.price=random.choice([350,360,370,380,390,400])
		elif self.bed ==2:
			self.bat=random.choice([1,2])
			self.price=random.choice([450,470,500,520,550])
		elif self.bed ==3:
			self.bat=random.choice([1,2,3])
			self.price=random.choice([700,730,750,770,800])
		
			



		

	
	def get_body_mail(self):

		try:
			c = self.conn.cursor()
			# c.execute("SELECT * FROM account WHERE runing = 0")
			sql = "SELECT * FROM settings  WHERE name = 'mail' ORDER BY random() LIMIT 1" 
			c.execute(sql)
			mail =c.fetchone()
			
			m= self.get_formated_data(c.description,mail)
			return m['value']
		except:
			return None
	def get_body_mail(self):

		try:
			c = self.conn.cursor()
			# c.execute("SELECT * FROM account WHERE runing = 0")
			sql = "SELECT * FROM settings  WHERE name = 'mail' ORDER BY random() LIMIT 1" 
			c.execute(sql)
			mail =c.fetchone()
			
			m= self.get_formated_data(c.description,mail)
			return m['value']
		except:
			return None
	
	

	

	

	def get_formated_data(self,headers,data):
		try:
			data = dict(zip([c[0] for c in headers], data))
		except:
			data = None
		return data
	def link_save(self,link):
		with open('links.txt', 'a') as file:
			file.write(link+"\n")


