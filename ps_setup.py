import sqlite3
import os.path
from os import path
import os
import random
import string
def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase

    return ''.join(random.choice(letters) for i in range(stringLength))

def Create_db(randomString):
    if path.exists(randomString+".db"):
        #os.remove(randomString+".db")
        f = open('data/'+randomString+".db","w+")
    else:
        f = open('data/'+randomString+".db","w+")
    return randomString
databessname = 'databases'#randomString(10)


conn = sqlite3.connect('data/'+databessname+".db")
print(databessname)
def ps_tebl_insert(conn):
    c = conn.cursor()
    c.execute("CREATE TABLE account (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, runing INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE proxys (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, checked INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE conversation (id INTEGER PRIMARY KEY AUTOINCREMENT, acc INTEGER NOT NULL DEFAULT 0, name TEXT NOT NULL DEFAULT 0, chat_id TEXT NOT NULL DEFAULT 0,send INTEGER DEFAULT 0)")


    conn.commit()

    return True






def ps_setup(profileID):
    Create_db(profileID)
    ps_tebl_insert(conn)
    return conn
ps_setup()






