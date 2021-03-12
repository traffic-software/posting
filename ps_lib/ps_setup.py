import sqlite3
from os import path
import random
import string
class table:
    def __del__(self):
        self.conn.close()
    def __init__(self):
        if self.dbfile():
            self.conn = sqlite3.connect('data/databases.db')

        else:
            self.conn = sqlite3.connect('data/databases.db')
            self.proxys_tebl_create()
            self.account_tebl_create()
            self.post_tebl_create()

    def dbfile(self):

        if path.exists('data/databases.db'):
            return True

        else:
            open('data/databases.db', "w+")
            return False

    def proxys_tebl_create(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE proxys (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, checked INTEGER DEFAULT 0)")
        self.conn.commit()
        return True

    def post_tebl_create(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT NOT NULL DEFAULT 0, body TEXT NOT NULL DEFAULT 0)")
        self.conn.commit()

        return True

    def account_tebl_create(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, runing INTEGER DEFAULT 0)")
        self.conn.commit()
        return True


    def randomString(self,stringLength=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase

        return ''.join(random.choice(letters) for i in range(stringLength))
















