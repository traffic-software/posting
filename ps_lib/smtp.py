
from ps_lib.ps_str import ps_str
from ps_lib.accounts import accounts
from ps_lib.imap import imap
from ps_lib.ps_setup import table
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
        
        
        one_account = acc.get_account()
        ps_data = one_account['data'].split(":")
        print(ps_data)
        

        popmail = imap(ps_data[0], ps_data[1], ps_data[2])
        # popmail = imap('obishop54@yahoo.com', 'uykgeqwivulqubib', 'imap.mail.yahoo.com')
        popmail.messages('replyad@bakecaincontrii.com')
        if popmail.ps_messges == None:
            print('next')
            continue
        for m in popmail.ps_messges:
            bot_body =text.Spin()
            print(m)
            
            bot_body = bot_body.replace('[name]', m['from_fullname'].replace('"',''))
           
            if ("replyad" in m['from_mail']) and (setup.checkReply(m['from_mail']) ==None):
                password = ps_data[1]  # ps_data[1] or  getpass('opnqvheifcpsxrel')
                sender = ps_data[0] #ps_data[0]
                email = Forger(sender)
                email.add_recipient(m['from_mail'])
                
                email.add_part(bot_body, "plain")
                email.make_email()  # Build the mail
                setup.replySave(sender,m['from_mail'])
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
        break
    return True


