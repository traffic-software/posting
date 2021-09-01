
import threading
from email.message import EmailMessage
from email.utils import formataddr
from smtplib import SMTP
import ssl
from ps_lib.ps_str import ps_str
from ps_lib.accounts import accounts
from ps_lib.imap import imap
from ps_lib.ps_setup import table
# from PyEmailTools.Forger import Forger
# from PyEmailTools.SmtpClient import SmtpClient
from getpass import getpass
import re

def reply_check(id=1):
    acc = accounts()
    setup = table()
    
    my_file = open('reply_text.txt','r')
    bot_body = my_file.read()
    my_file.close()
    text=ps_str(bot_body)
    for x in range(3):
        
        
        ac = acc.get_account_for_lead_find()
        print('reply chcking : ',ac['email'])
        
       
        

        popmail = imap(ac['id'],ac['email'],ac['password'])
        popmail.messages('replyad@bakecaincontrii.com')
        # popmail.messages()
        # popmail.messages()
        if popmail.ps_messges == None:
            continue
        for m in popmail.ps_messges:
            m['body']='ok'
            bot_body =text.Spin()
            
            bot_body = bot_body.replace('[name]', '')
           
            if ("replyad" in m['from_mail']) and (setup.checkReply(m['Reply_To']) ==None):
                password = ac['password']  # ps_data[1] or  getpass('opnqvheifcpsxrel')
                sender = ac['email']
                setup.replySave(sender,m['Reply_To'],m['sub'])
                print("reply find")
            else:
                print(ac['email'],m['from_mail'])
        popmail.close()
        
    return True

def reply_start():
	ths = []
	pid = threading.local()
	try:
		th = threading.Thread(target=reply_check)
		ths.append(th)
		th.setName('mail_pop')
		th.start()
	except:
		print('reply start problelm')
	return True
def reply_test():
        
        
        data = ['UstenkoSV@yahoo.com', 'gzwqbxxrjwktkmuh', 'imap.mail.yahoo.com']#account['data'].split(":")
        bot_body = 'ok'
            
        password = data[1]  # ps_data[1] or  getpass('opnqvheifcpsxrel')
        sender = data[0] #ps_data[0]
        email = EmailMessage()
        email['Subject'] = 'ok now 2'
        email['From'] = sender#formataddr(("Sender's Name", m['Reply_To']))
        email['Reply-To'] = sender#formataddr(("Name of Reply2", "email2@domain2.com"))
        # email['In-Reply-To'] = 'UstenkoSV1@yahoo.com'#formataddr(("Name of Reply2", "email2@domain2.com"))
        email['To'] = 'call77386@gmail.com'#formataddr(("John Smith", "john.smith@gmail.com"))
        
        email.set_content(bot_body, subtype='plain')
        try:
            server = SMTP('smtp.mail.yahoo.com', 587)
            server.ehlo() # Can be omitted
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo() # Can be omitted
            server.login(sender, password)
            server.sendmail(sender,'call77386@gmail.com',email.as_string())
        except Exception as e:
            # Print any error messages to stdout
            print(e)
        finally:
            server.quit()





