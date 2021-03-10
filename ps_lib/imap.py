import email
import imaplib
import re


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
		tmp, data = self.i.search('utf8', '(FROM {})'.format(site_email))
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

		self.close()
		return messages
	def get_body(self,e):
		# Body details
		for part in e.walk():
			if part.get_content_type() == "text/plain":
				body = part.get_payload(decode=True)
				return body.decode('utf-8')
				break
			else:
				continue
	def get_link(self):
		for m in self.ps_messges:
			x = re.findall(r"sd", m)
			print(x)

		self.ps_messges=None


	def close(self):
		self.i.close()
		self.i.logout()


popmail = imap('aliviafarnsworth007@gmail.com', "CXQrJ7Rnq75nQaLf", 'imap.gmail.com')
popmail.messages('malaknoyn100@gmail.com')
popmail.get_link()
