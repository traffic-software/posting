import sqlite3
from os import path
from sys import exit
import sys
import random
import string
import requests
# import winreg
import os
import time
from datetime import datetime


class table:
    REG_PATH = r"Control Panel\Mouse"
    consumer_key = 'ck_7ce53f974f6ebf45de1394b4544f1951fe602413'
    consumer_secret = 'cs_f828c575f480a0a1be5f80f6661ef2957bec9c80'
    License = None

    def __init__(self):
        abspath = os.path.abspath(__file__)
        self.dname = os.path.dirname(abspath)

        self.databasesfile = self.dname+'/databases.db'

        if self.dbfile():
            self.conn = sqlite3.connect(self.databasesfile)
            self.host_verify()

        else:
            self.conn = sqlite3.connect(self.databasesfile)
            self.proxys_tebl_create()
            self.account_tebl_create()
            self.post_tebl_create()
            self.settings_tebl_create()
            self.reply_tebl_create()
            self.host_verify()
            self.token_verify()

    def dbfile(self):

        if path.exists(self.databasesfile):
            return True

        else:
            open(self.databasesfile, "w+")
            return False

    def proxys_tebl_create(self):
        c = self.conn.cursor()
        c.execute(
            "CREATE TABLE proxys (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, checked INTEGER DEFAULT 0)")
        self.conn.commit()
        return True

    def post_tebl_create(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT NOT NULL DEFAULT 0, body TEXT NOT NULL DEFAULT 0)")
        self.conn.commit()

        return True

    def account_tebl_create(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, runing INTEGER DEFAULT 0,used_at TEXT DEFAULT 0)")
        self.conn.commit()
        return True

    def settings_tebl_create(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE settings (name TEXT NOT NULL,value TEXT NOT NULL)")
        self.conn.commit()
        return True

    def replyOn(self):
        c = self.conn.cursor()
        c.execute("INSERT INTO settings (name,value) VALUES  (?,?)",
                  ['reply', 1])
        self.conn.commit()

    def replyOff(self):
        c = self.conn.cursor()
        c.execute("DELETE FROM settings WHERE name = 'reply'")
        self.conn.commit()

    def checkReplyOn(self):
        c = self.conn.cursor()
        sql = "SELECT * FROM settings WHERE name = '{}'".format('reply')
        c.execute(sql)
        post = c.fetchone()
        data = self.get_formated_data(c.description, post)
        return data

    def replySave(self, acc_mail, lead_mail, sub):

        url = 'https://{host}/api/v1/post/account/lead/{token}'.format(
            host=self.host_get(), token=self.token)
        params = {'lead_mail': lead_mail, "acc_mail": acc_mail, 'sub': sub}

        r = requests.get(url, params=params)
        if "error" in r.json():
            print("token error")

        return True

    def checkReply(self, tomail):
        c = self.conn.cursor()
        sql = "SELECT * FROM reply WHERE tomail = '{}'".format(tomail)

        c.execute(sql)
        post = c.fetchone()
        data = self.get_formated_data(c.description, post)
        print(data)
        return data

    def reply_tebl_create(self):
        c = self.conn.cursor()
        c.execute(
            "CREATE TABLE reply (frommail TEXT NOT NULL,tomail TEXT NOT NULL)")
        self.conn.commit()
        return True

    def license_verify(self):
        licens = self.license_get()
        # #{"success":true,"data":{"id":48,"orderId":279,"productId":277,"userId":1,"licenseKey":"workerBAZL9-09W3B-PHUZQ-0JZ8Z-7AFZJ","expiresAt":"2021-04-15 03:47:18","validFor":30,"source":1,"status":2,"timesActivated":null,"timesActivatedMax":1,"createdAt":"2021-03-16 03:47:18","createdBy":1,"updatedAt":"2021-03-16 03:47:18","updatedBy":1}}

        # if licens== None:
        #     self.License =  str(input("please enter your license key : "))

        #     self.license_active()
        #     self.license_save()
        #     self.set_reg("ps", self.License)

        # else:
        #     self.License = licens['value']
        # url = 'https://mailorigin.com/wp-json/lmfwc/v2/licenses/{license}?consumer_key={consumer_key}&consumer_secret={consumer_secret}'.format(license=self.License,consumer_key=self.consumer_key,consumer_secret=self.consumer_secret)

        # r = requests.get(url)
        # if "code" in r.json():
        #     time.sleep(60)
        #     print("license key error")
        #     exit()
        # else:
        #     l=r.json()

        #     expiresAt =l['data']['expiresAt'][0:10]
        #     now = datetime.now()
        #     if self.time_diff(expiresAt,now.strftime('%Y-%m-%d'))<1:
        #         print("you need buy new license")
        #         time.sleep(60)
        #         exit()
        #     if self.get_reg('ps') == None:
        #         print("license key error")
        #         time.sleep(60)
        #         exit()
        #     if not (self.License == self.get_reg('ps')):
        #         print("license key error")
        #         time.sleep(60)
        #         exit()
        return True

    def token_verify(self):
        token = self.token_get()
        try:

            if token == None:
                if sys.platform not in ['Windows', 'win32', 'cygwin']:
                    self.token = os.environ['PS_KEY']
                else:
                    self.token = str(input("please enter your api_token : "))
                self.token_save()

            else:
                self.token = token['value']
            url = 'https://{host}/api/v1/post/info/{token}'.format(
                host=self.host_get(), token=self.token)

            r = requests.get(url, timeout=15)
            if "error" in r.json():

                print(r.json()['message'])
                exit()
        except:
            print('network requst timeout in 15')
            return False

        return True

    def pop_verify(self):
        popmail = self.pop_get()
        if popmail == None:
            self.popmail = str(
                input("please enter your popMail or pva_pop : "))
            self.pop_save()
        else:
            self.popmail = popmail['value']

        return self.popmail

    def pop_get(self):
        c = self.conn.cursor()
        sql = "SELECT * FROM settings WHERE name = '{}'".format('popmail')
        c.execute(sql)
        post = c.fetchone()
        return self.get_formated_data(c.description, post)

    def pop_save(self):
        c = self.conn.cursor()
        c.execute("INSERT INTO settings (name,value) VALUES  (?,?)",
                  ['popmail', self.popmail])
        self.conn.commit()

    def pva_verify(self):
        make_pva = self.pva_get()
        if make_pva == None:
            self.make_pva = str(
                input("your make pva using this software yes or no : "))
            self.pva_save()
        else:
            self.make_pva = make_pva['value']

        return self.make_pva

    def pva_get(self):
        c = self.conn.cursor()
        sql = "SELECT * FROM settings WHERE name = '{}'".format('make_pva')
        c.execute(sql)
        post = c.fetchone()
        return self.get_formated_data(c.description, post)

    def pva_save(self):
        c = self.conn.cursor()
        c.execute("INSERT INTO settings (name,value) VALUES  (?,?)",
                  ['make_pva', self.make_pva])
        self.conn.commit()

    def token_off(self):
        token = self.token_get()
        self.token = token['value']

        url = 'https://{host}/api/v1/post/off/{token}'.format(
            host=self.host_get(), token=self.token)

        r = requests.get(url)

        if "off" in r.json():
            return True
        else:
            return False

    def host_verify(self):
        host = self.host_get()
        if host == None:
            # str(input("please enter your api_token : "))
            self.host = os.environ['PS_HOST']
            self.host_save()
        return host

    def proxyhorse_verify(self, api_key):
        ph_t = self.proxyhorse_get()

        return ph_t

    def proxyhorse_get(self):
        c = self.conn.cursor()
        sql = "SELECT * FROM settings WHERE name = '{}'".format('ph_token')
        c.execute(sql)
        post = c.fetchone()
        data = self.get_formated_data(c.description, post)
        if data == None:
            return data
        return data['value']

    def proxyhorse_save(self, token):
        c = self.conn.cursor()
        c.execute("INSERT INTO settings (name,value) VALUES  (?,?)",
                  ['ph_token', token])
        self.conn.commit()

    def time_diff(self, start, end):

        FMT = '%Y-%m-%d'
        tdelta = datetime.strptime(start, FMT) - datetime.strptime(end, FMT)
        return tdelta.days

    def license_save(self):
        c = self.conn.cursor()
        c.execute("INSERT INTO settings (name,value) VALUES  (?,?)",
                  ['license', self.License])
        self.conn.commit()

    def token_save(self):
        c = self.conn.cursor()
        c.execute("INSERT INTO settings (name,value) VALUES  (?,?)",
                  ['token', self.token])
        self.conn.commit()

    def pop_save(self):
        c = self.conn.cursor()
        c.execute("INSERT INTO settings (name,value) VALUES  (?,?)",
                  ['popmail', self.popmail])
        self.conn.commit()

    def host_save(self):
        c = self.conn.cursor()
        c.execute("INSERT INTO settings (name,value) VALUES  (?,?)",
                  ['host', self.host])
        self.conn.commit()

    def license_active(self):
        url = 'https://mailorigin.com/wp-json/lmfwc/v2/licenses/activate/{license}?consumer_key={consumer_key}&consumer_secret={consumer_secret}'.format(
            license=self.License, consumer_key=self.consumer_key, consumer_secret=self.consumer_secret)

        r = requests.get(url)
        if "code" in r.json():
            print("license key error")
            exit()
        else:
            return True

    def token_get(self):
        c = self.conn.cursor()
        sql = "SELECT * FROM settings WHERE name = '{}'".format('token')
        c.execute(sql)
        post = c.fetchone()
        return self.get_formated_data(c.description, post)

    def pop_get(self):
        c = self.conn.cursor()
        sql = "SELECT * FROM settings WHERE name = '{}'".format('popmail')
        c.execute(sql)
        post = c.fetchone()
        return self.get_formated_data(c.description, post)

    def host_get(self):
        c = self.conn.cursor()
        sql = "SELECT * FROM settings WHERE name = '{}'".format('host')
        c.execute(sql)
        post = c.fetchone()
        data = self.get_formated_data(c.description, post)
        if data == None:
            return data
        return data['value']

    def software_token(self):
        c = self.conn.cursor()
        sql = "SELECT * FROM settings WHERE name = '{}'".format('token')
        c.execute(sql)
        post = c.fetchone()
        data = self.get_formated_data(c.description, post)
        return data['value']

    def license_get(self):
        c = self.conn.cursor()
        sql = "SELECT * FROM settings WHERE name = '{}'".format('license')
        c.execute(sql)
        post = c.fetchone()
        return self.get_formated_data(c.description, post)

    def get_formated_data(self, headers, data):
        try:
            data = dict(zip([c[0] for c in headers], data))
        except:
            data = None
        return data

    def randomString(self, stringLength=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase

        return ''.join(random.choice(letters) for i in range(stringLength))

    # def set_reg(self,name, value):
    #     try:
    #         winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REG_PATH)
    #         registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH, 0,
    #                                       winreg.KEY_WRITE)
    #         winreg.SetValueEx(registry_key, name, 0, winreg.REG_SZ, value)
    #         winreg.CloseKey(registry_key)
    #         return True
    #     except WindowsError:
    #         return False

    # def get_reg(self,name):
    #     try:
    #         registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH, 0,
    #                                       winreg.KEY_READ)
    #         value, regtype = winreg.QueryValueEx(registry_key, name)
    #         winreg.CloseKey(registry_key)
    #         return value
    #     except WindowsError:
    #         return None
