import sqlite3
import os
import requests
from sys import exit
from ps_lib.ps_setup import table
from datetime import datetime
from datetime import timedelta
class accounts:

    def __init__(self):
        self.conn = sqlite3.connect('data/databases.db')
        self.software = table()


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


    def get_account(self):
        url = 'http://{host}/api/v1/post/account/{token}'.format(host=self.software.host_verify(),token=self.software.software_token())

        r = requests.get(url)
        if "error" in r.json():
            print("error",r.json()['message'])
            exit()
        return r.json()["data"]
        
    def get_account_for_lead_find(self):
        url = 'http://{host}/api/v1/post/account/rendom/{token}'.format(host=self.software.host_verify(),token=self.software.software_token())

        r = requests.get(url)
        if "error" in r.json():
            print("error",r.json()['message'])
            exit()
        return r.json()["data"]
        

    def get_formated_data(self, headers, data):
        try:
            data = dict(zip([c[0] for c in headers], data))
        except:
            data = None
        return data

    def account_Reactive(self):
        c = self.conn.cursor()
        now = datetime.now()+ timedelta(days= -3)
        
        
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
    def ban_3(self,id,status=1):
        url = 'http://{host}/api/v1/post/account/ban/{token}/{id}'.format(host=self.software.host_verify(),token=self.software.software_token(),id=id)

        params = {'status': status}
        r = requests.get(url,params=params)
        if "error" in r.json():
            print("error",r.json()['message'])
            exit()
        return r.json()
    def post_done(self,id,messasge='post done'):
        url = 'http://{host}/api/v1/post/account/postdone/{token}/{id}'.format(host=self.software.host_verify(),token=self.software.software_token(),id=id)

        params = {'data': messasge}
        r = requests.get(url,params=params)
        if "error" in r.json():
            print("error",r.json()['message'])
            exit()
        return r.json()
    def post_error(self,id,message="default messge"):
        url = 'http://{host}/api/v1/post/account/posterror/{token}/{id}'.format(host=self.software.host_verify(),token=self.software.software_token(),id=id)

        params = {'data': message}
        r = requests.get(url,params=params)
        if "error" in r.json():
            print("error",r.json()['message'])
            exit()
        return r.json()
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

