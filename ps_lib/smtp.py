
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
        if setup.checkReplyOn() == None:
            break
        
        one_account = acc.get_account()
        ps_data = one_account['data'].split(":")
        

        popmail = imap(ps_data[0], ps_data[1], ps_data[2])
        # popmail = imap('obishop54@yahoo.com', 'uykgeqwivulqubib', 'imap.mail.yahoo.com')
        popmail.messages()
        if popmail.ps_messges == None:
            print('next')
            continue
        for m in popmail.ps_messges:
            bot_body =text.Spin()
            
            bot_body = bot_body.replace('[name]', m['from_fullname'].replace('"',''))
           
            if ("reply.craigslist.org" in m['from_mail']) and (setup.checkReply(m['from_mail']) ==None):
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
reply_with_smtp()

