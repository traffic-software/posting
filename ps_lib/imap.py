import email
import imaplib
import re
from ps_lib.ps_str import ps_str



class imap:
	i = False
	ps_messges=None

	def __init__(self, username, password, host):
		self.username = username
		self.password = password
		self.host = host
		self.login()

	def login(self):
		# connect to host using SSL
		self.i = imaplib.IMAP4_SSL(self.host)
		self.i.login(self.username, self.password)
		self.i.select('Inbox')

	def messages(self,site_email):
		# tmp, data = self.i.search('utf8','(UNSEEN)')
		tmp, data = self.i.search('utf8', '(TO {})'.format(site_email))
		messages = []

		for num in data[0].split():
			tmp, data = self.i.fetch(num, '(RFC822)')

			# print('Message %s\n%s\n' % (num, data[0][1]))
			raw_email_string = data[0][1].decode('utf-8')
			psm = email.message_from_string(raw_email_string)
			if psm:
				messages.append(self.get_body(psm))


			self.i.store(num,'+FLAGS', '\\Deleted')
		self.ps_messges = messages
		self.i.expunge()


		return messages
	def get_body(self,e):
		# Body details
		for part in e.walk():
			if part.get_content_type() == "text/html":
				body = part.get_payload(decode=True)
				#body.decode('utf-8')
				return body
				break
			else:
				continue
	def get_link(self):
		urls=[]
		for m in self.ps_messges:
			st = ps_str(m)
			#https://torino.bakecaincontrii.com/fe/main.php?page=post_publish&idp=1de787b50fac053f65223f333d24b16a
			url = st.find_urls("main.php?page=post_publish&idp=")
			if url!=None:
				urls.append(url)
				break




		self.ps_messges=None
		return urls


	def close(self):
		self.i.close()
		self.i.logout()

popmail = imap('bonacatagreco100@gmail.com', "mdmdmdmd123", 'imap.gmail.com')
popmail.messages("elizabethgreen1932@gmail.com")



