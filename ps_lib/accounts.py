import sqlite3
import os
from sys import exit
from datetime import datetime
from datetime import timedelta
class accounts:

    def __init__(self):
        self.conn = sqlite3.connect('data/databases.db')


    def ps_proxys_insert(self, proxys):

        c = self.conn.cursor()

        c.executemany("INSERT INTO proxys (data,checked) VALUES  (?,?)", proxys)
        self.conn.commit()

    def ps_proxys_save(self):

        with open('proxy.txt', encoding="utf8") as my_file:
            lines = my_file.readlines()
            my_file.truncate()
        proxy = []
        for key, line in enumerate(lines):
            ps_data = line.rstrip("\n")
            # .split(":")
            # print(ps_data)

            # host = ps_data[0]
            # port = ps_data[1].rstrip("\n")
            proxy_tada = (ps_data, 0)  # (host+":"+port,0)
            proxy.append(proxy_tada)
        self.ps_proxys_insert(proxy)
    def insert(self,combos):
        c = self.conn.cursor()
        c.executemany("INSERT INTO accounts (data,runing,used_at) VALUES  (?,?,?)", combos)
        self.conn.commit()


    def get_accounts(self,limit):
        c = self.conn.cursor()
        # c.execute("SELECT * FROM account WHERE runing = 0")
        sql = "SELECT * FROM accounts WHERE runing = 1 ORDER BY random() LIMIT " + str(limit)
        c.execute(sql)
        account = c.fetchall()
        # c.fetchall()
        # c.fetchmany()
        # c.fetchone()
        self.conn.commit()
        return account

    def get_account(self):
        c = self.conn.cursor()
        now = datetime.now()+ timedelta(days= -0)
        
        sql = "SELECT * FROM accounts WHERE runing = 1 AND used_at <= '{used}' ORDER BY random() LIMIT 1".format(used=now.strftime('%Y-%m-%d'))
        c.execute(sql)
        a = c.fetchone()
        a = self.get_formated_data(c.description,a)
        
        
        return a

    def get_formated_data(self, headers, data):
        try:
            data = dict(zip([c[0] for c in headers], data))
        except:
            data = None
        return data

    def account_Reactive(self):
        c = self.conn.cursor()
        now = datetime.now()+ timedelta(days= -2)
        
        
        # c.execute("SELECT * FROM account WHERE runing = 0")
        sql = "UPDATE accounts SET runing =1 WHERE used_at <= '{used}' AND  runing = 0".format(used=now.strftime('%Y-%m-%d'))
        c.execute(sql)
        self.conn.commit()

    def account_active(self,id):
        c = self.conn.cursor()
        # c.execute("SELECT * FROM account WHERE runing = 0")
        sql = "UPDATE accounts SET runing =1 WHERE id = " + str(id)
        c.execute(sql)
        self.conn.commit()

    def account_inactive(self,id):
        c = self.conn.cursor()
        # c.execute("SELECT * FROM account WHERE runing = 0")
        sql = "UPDATE accounts SET runing =0 WHERE id = " + str(id)
        c.execute(sql)
        self.conn.commit()

    def ban(self,id):
        c = self.conn.cursor()
        # c.execute("SELECT * FROM account WHERE runing = 0")
        sql = "UPDATE accounts SET runing =2 WHERE id = " + str(id)
        c.execute(sql)
        self.conn.commit()
    def post_done(self,id):
        c = self.conn.cursor()
        now = datetime.now()+ timedelta(days= -1)
        sql = "UPDATE accounts SET used_at < '{used}' WHERE id = {id}".format(used=now.strftime('%Y-%m-%d'),id=str(id)) 
        c.execute(sql)
        self.conn.commit()
    def save(self):

        my_file = open('account.txt', 'r+', encoding="utf8")
        lines = my_file.readlines()
        my_file.truncate(0)
        my_file.close()

        list_data = []
        for key, line in enumerate(lines):
            try:
                ps_data = line.split(":")
                print(ps_data)
                username = ps_data[0]
                password = ps_data[1]
                host = ps_data[2].rstrip("\n")
                now = datetime.now()+ timedelta(days= -3)
                
                combos_tada = (username+":"+password+":"+host, 1,now.strftime('%Y-%m-%d'))
                list_data.append(combos_tada)
            except:
                print('data format problem please check your data in account file')
        self.insert(list_data)

