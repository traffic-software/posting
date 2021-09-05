import sqlite3
from sys import exit
from ps_lib.ps_setup import table
import requests
import time
class helper:

	def __init__(self):
		self.software = table()
		self.db = sqlite3.connect(self.software.databasesfile)

	def all_account_active(self):
		c = self.db.cursor()
		sql = "UPDATE accounts SET runing =1 WHERE runing =0"
		c.execute(sql)
		self.db.commit()

	def all_account_delete(self):
		c = self.db.cursor()
		sql = "DELETE FROM accounts"
		c.execute(sql)
		self.db.commit()
	def account_delete(self,id):
		c = self.db.cursor()
		sql = "DELETE FROM accounts WHERE id = "+str(id)
		c.execute(sql)
		self.db.commit()

	def account_inactive(self,id):
		c = self.db.cursor()
		# c.execute("SELECT * FROM account WHERE runing = 0")
		sql = "UPDATE accounts SET runing =0 WHERE id = "+str(id)
		c.execute(sql)
		self.db.commit()
	def account_ban(self,id):
		c = self.db.cursor()
		sql = "UPDATE accounts SET runing =2 WHERE id = "+str(id)
		c.execute(sql)
		self.db.commit()
	
	def network_check(self):

		while True:
			try:
				r = requests.get('https://api.myip.com', timeout=1)
				break
			except:
				print('network_check : plz check your  network connection')
				time.sleep(60)
				continue
			
