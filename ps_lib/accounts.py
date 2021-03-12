import sqlite3
import os
class accounts:
    def __del__(self):
        self.conn.close()
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
        c.executemany("INSERT INTO accounts (data,runing) VALUES  (?,?)", combos)
        self.conn.commit()


    def get_accounts(self,limit):
        c = self.conn.cursor()
        # c.execute("SELECT * FROM account WHERE runing = 0")
        sql = "SELECT * FROM accounts WHERE runing = 0 ORDER BY random() LIMIT " + str(limit)
        c.execute(sql)
        account = c.fetchall()
        # c.fetchall()
        # c.fetchmany()()
        # c.fetchone()
        self.conn.commit()
        return account

    def get_account(self):
        c = self.conn.cursor()
        # c.execute("SELECT * FROM accounts WHERE runing = 0")
        c.execute("SELECT * FROM accounts WHERE runing = 0 ORDER BY random() LIMIT 1")
        a = c.fetchone()
        self.conn.commit()
        a = self.get_formated_data(c.description,a)
        return a

    def get_formated_data(self, headers, data):
        data = dict(zip([c[0] for c in headers], data))
        return data
    def get_account_for_inactive(self):
        file = open('active.txt', "r+")
        lines = file.readlines()

        file.truncate()

        print(lines)
        # print(type(lines))
        list_data = []
        for line in lines:
            account_id = line.rstrip("\n")
            self.account_inactive(account_id)
            open('active.txt', "w+")

    def account_active(self,acc_id):
        c = self.conn.cursor()
        # c.execute("SELECT * FROM account WHERE runing = 0")
        sql = "UPDATE accounts SET runing =1 WHERE id = " + str(acc_id)
        c.execute(sql)
        self.conn.commit()

    def account_inactive(self,id):
        c = self.conn.cursor()
        # c.execute("SELECT * FROM account WHERE runing = 0")
        sql = "UPDATE accounts SET runing =0 WHERE id = " + str(id)
        c.execute(sql)
        self.conn.commit()

    def account_ban(self,id):
        c = self.conn.cursor()
        # c.execute("SELECT * FROM account WHERE runing = 0")
        sql = "UPDATE accounts SET runing =2 WHERE id = " + str(id)
        c.execute(sql)
        self.conn.commit()
    def save(self):

        my_file = open('account.txt', 'r+', encoding="utf8")
        lines = my_file.readlines()
        my_file.truncate()
        list_data = []
        for key, line in enumerate(lines):


            ps_data = line.split(":")
            username = ps_data[0]
            password = ps_data[1].rstrip("\n")
            combos_tada = (username+":"+password, 0)
            list_data.append(combos_tada)
        self.insert(list_data)

