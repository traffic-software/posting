import email
import imaplib
import ssl
import re
from sys import exit
import json
import requests
try:
    from ps_lib.ps_str import ps_str
    from ps_lib.accounts import accounts
except:
    from ps_str import ps_str
    from accounts import accounts

from imapclient import IMAPClient


class imap:
    i = False
    ps_messges = None

    def __init__(self, account_id=False, username=False, password=False, hosturl=False):
        self.username = username
        self.password = password
        self.hosturl = hosturl
        if hosturl == False:
            if 'yahoo' in self.username:
                self.hosturl = 'imap.mail.yahoo.com'
            elif 'gmail' in self.username:
                self.hosturl = 'imap.gmail.com'
            elif 'hotmail' in self.username:
                self.hosturl = 'imap-mail.outlook.com'
            elif 'outlook' in self.username:
                self.hosturl = 'outlook.office365.com'

        self.i = IMAPClient(host=self.hosturl)

        try:
            self.login()
        except:
            if account_id:
                acc = accounts()
                acc.ban_3(account_id)

    def login(self):
        # connect to host using SSL
        self.i.login(self.username, self.password)
        self.i.select_folder('INBOX')

    def messages(self, mail_from=None):
        self.ps_messges = None

        try:

            if mail_from == None:
                messages = self.i.search('UNSEEN')

            else:
                messages = self.i.search(
                    '(FROM "{}" UNSEEN)'.format(mail_from))

        except:
            messages = None
            print('mesage none')

        m = self.i.fetch(messages, 'RFC822')

        if len(m) < 1:
            print('no mesage')

            return False
        else:
            len(m)
        mes = []
        for uid, data in m.items():
            data = data[b'RFC822']
            mailmessage = email.message_from_bytes(data)

            try:
                m = {}

                m['body'] = self.get_body(mailmessage)
                text = ps_str(mailmessage.get("from"))

                m['from_mail'] = text.find_email(
                    '([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)')
                m['sub'] = mailmessage.get("Subject")
                m['Reply_To'] = mailmessage.get("Reply-To")
                mes.append(m)

            except:
                print('problme in message')

            self.ps_messges = mes
            # self.i.delete_messages(uid)
        return self.ps_messges

    def get_body(self, e):
        # Body details

        for part in e.walk():

            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True)

                return body

            else:
                continue

    def get_link(self, condition=None):
        try:
            urls = []
            if None == self.ps_messges:
                return urls
            for m in self.ps_messges:

                st = ps_str(m['body'])
                print('link search')
                # https://torino.bakecaincontrii.com/fe/main.php?page=post_publish&idp=1de787b50fac053f65223f333d24b16a
                for text in condition:
                    url = st.find_urls(text)
                    if url != None:
                        print('one link find')
                        urls.append(url)
        except:
            print('link search problem')
        self.ps_messges = None

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
