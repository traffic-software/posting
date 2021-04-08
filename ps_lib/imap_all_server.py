from imapclient import IMAPClient


# context manager ensures the session is cleaned up
# with IMAPClient(host="imap.mail.yahoo.com") as client:

client= IMAPClient(host="outlook.office365.com")
# client.login('KaydeBoeve1990@yahoo.com', 'zaubwiiimufhkkrc')
client.login('cindiapogfw@hotmail.com', 'yn1dybq0dM5')
client.select_folder('INBOX')
messages = client.search('UNSEEN')
messages = client.fetch(messages,'RFC822')
for uid, data in messages.items():
    
    client.delete_messages(uid)
    data = data[b'RFC822']
    mailmessage = email.message_from_bytes(data)
    try:
        print('conected')
        print(print(uid, mailmessage.get("From"), mailmessage.get("Subject")))
    except:
        print('problem')
    print('..........................................................')
client.logout()
# client.shutdown()