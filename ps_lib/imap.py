import email
import imaplib
import ssl
import re
from sys import exit
import json, requests
try:
	from ps_lib.ps_str import ps_str
	from ps_lib.accounts import accounts
except:
	from ps_str import ps_str
	from accounts import accounts

from imapclient import IMAPClient


class imap:
	i = False
	ps_messges=None
	

	def __init__(self, username, password, hosturl):
		self.username = username
		self.password = password
		self.hosturl = hosturl
		self.i= IMAPClient(host=hosturl)
		self.login()
		

	def login(self):
		# connect to host using SSL
		self.i.login(self.username, self.password)
		self.i.select_folder('INBOX')

	def messages(self,mail_from=None):
		self.ps_messges = None
		mailbodys = []
		
		messages = self.i.search('UNSEEN')
		print('message search')
		m = self.i.fetch(messages,'RFC822')
		
		
		if len(m) <1:
			print('message not fund')
			return False
		for uid, data in m.items():
			data = data[b'RFC822']
			mailmessage = email.message_from_bytes(data)
			try:
				
				mailbodys.append(self.get_body(mailmessage))
				# print(print(uid, mailmessage.get("From"), mailmessage.get("Subject")))
			except:
				print('problme in message')
			
			self.ps_messges = mailbodys
			self.i.delete_messages(uid)
		return messages
	def get_body(self,e):
		# Body details
		
		
		for part in e.walk():
			
			if part.get_content_type() == "text/html":
				body = part.get_payload(decode=True)
				return body
				
			else:
				continue
	def get_link(self):
		urls=[]
		try:
			for m in self.ps_messges:
				
				st = ps_str(m)
				print('link search')
				#https://torino.bakecaincontrii.com/fe/main.php?page=post_publish&idp=1de787b50fac053f65223f333d24b16a
				url = st.find_urls("main.php?page=post_publish")
				
				if url!=None:
					print('one link find')
					urls.append(url)
					
		except:
			print('link search problem')
		self.ps_messges=None
		print(urls)
		return urls


	def close(self):
		self.i.logout()
		# self.i.shutdown()

# while True:
# 	acc = accounts()
# 	one_account = acc.get_account()
# 	ps_data = one_account['data'].split(":")
# 	acc.account_ban(one_account['id'])

# 	popmail = imap(ps_data[0], ps_data[1], ps_data[2])
# 	popmail.messages()
# 	popmail.get_link()
# 	popmail.close()






