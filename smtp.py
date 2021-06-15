
import threading
try:
    from ps_lib.ps_str import ps_str
    from ps_lib.accounts import accounts
    from ps_lib.imap import imap
    from ps_lib.ps_setup import table
except:
    from ps_str import ps_str
    from accounts import accounts
    from imap import imap
    from ps_setup import table
from PyEmailTools.Forger import Forger
from PyEmailTools.SmtpClient import SmtpClient
from getpass import getpass
import re

def reply_with_smtp():
    acc = accounts()
    setup = table()
    my_file = open('reply_text.txt','r')
    bot_body = my_file.read()
    my_file.close()
    text=ps_str(bot_body)
    
    
		
    
    

    while True:
        
        
        account = acc.get_account()
        data = account['data'].split(":")
        print(data)
        

        popmail = imap(data[0], data[1], data[2])
        # popmail = imap('obishop54@yahoo.com', 'uykgeqwivulqubib', 'imap.mail.yahoo.com')
        popmail.messages('replyad@bakecaincontrii.com')
        # popmail.messages()
        if popmail.ps_messges == None:
            continue
        for m in popmail.ps_messges:
            bot_body =text.Spin()
            print(m)
            
            bot_body = bot_body.replace('[name]', '')
           
            if ("replyad" in m['from_mail']) and (setup.checkReply(m['Reply_To']) ==None):
                password = data[1]  # ps_data[1] or  getpass('opnqvheifcpsxrel')
                sender = data[0] #ps_data[0]
                email = Forger(sender)
                email.add_recipient(m['Reply_To'])
                
                email.add_part(bot_body, "plain")
                email.make_email()  # Build the mail
                setup.replySave(sender,m['Reply_To'])
                if 'yahoo' in sender:
                    smtp_host= 'smtp.mail.yahoo.com'
                elif 'gmail' in sender:
                    smtp_host = 'smtp.gmail.com'
                elif 'hotmail' in sender:
                    smtp_host = 'smtp.live.com'
                elif 'outlook' in sender:
                    smtp_host = 'smtp-mail.outlook.com'
                

                smtpclient = SmtpClient(smtp=smtp_host, port=587, username=sender, password=password)
                smtpclient.send(email, sender, [m['from_mail']])
        popmail.close()
        
    return True

def reply_start():
	ths = []
	pid = threading.local()
	try:
		th = threading.Thread(target=reply_with_smtp)
		ths.append(th)
		th.setName('mail_pop')
		th.start()
	except:
		print('reply start problelm')
	return True
reply_start()


