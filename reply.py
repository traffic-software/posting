from os import path
if path.exists('data/databases.db'):
    import smtp
    smtp.reply_check()
