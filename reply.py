from os import path
import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
if path.exists(dname+'/ps_lib/databases.db'):
    import smtp
    print('call reply_check')
    smtp.reply_check()

