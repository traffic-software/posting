import sqlite3
from os import path
import random
import string
import requests
from datetime import datetime
class table:
    consumer_key = 'ck_7ce53f974f6ebf45de1394b4544f1951fe602413'
    consumer_secret = 'cs_f828c575f480a0a1be5f80f6661ef2957bec9c80'
    License = None
    def __init__(self):
        if self.dbfile():
            self.conn = sqlite3.connect('data/databases.db')
            self.license_verify()

        else:
            self.conn = sqlite3.connect('data/databases.db')
            self.proxys_tebl_create()
            self.account_tebl_create()
            self.post_tebl_create()
            self.settings_tebl_create()
            self.license_verify()

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
    def settings_tebl_create(self):
            c = self.conn.cursor()
            c.execute("CREATE TABLE settings (name TEXT NOT NULL,value TEXT NOT NULL)")
            self.conn.commit()
            return True
    def license_verify(self):
        licens = self.license_get()
        #{"success":true,"data":{"id":48,"orderId":279,"productId":277,"userId":1,"licenseKey":"workerBAZL9-09W3B-PHUZQ-0JZ8Z-7AFZJ","expiresAt":"2021-04-15 03:47:18","validFor":30,"source":1,"status":2,"timesActivated":null,"timesActivatedMax":1,"createdAt":"2021-03-16 03:47:18","createdBy":1,"updatedAt":"2021-03-16 03:47:18","updatedBy":1}}

        if licens== None:
            self.License =  str(input("please enter your license key : "))
            self.license_active()
            self.license_save()


        else:
            self.License = licens['value']
        url = 'https://mailorigin.com/wp-json/lmfwc/v2/licenses/{license}?consumer_key={consumer_key}&consumer_secret={consumer_secret}'.format(license=self.License,consumer_key=self.consumer_key,consumer_secret=self.consumer_secret)

        r = requests.get(url)
        if "code" in r.json():
            print("license key error")
            exit()
        else:
            l=r.json()

            expiresAt =l['data']['expiresAt'][0:10]
            now = datetime.now()
            if self.time_diff(expiresAt,now.strftime('%Y-%m-%d'))<1:
                print("you need buy new license")
                exit()




    def time_diff(self,start,end):

        FMT = '%Y-%m-%d'
        tdelta = datetime.strptime(start, FMT) - datetime.strptime(end, FMT)
        return tdelta.days
    def license_save(self):
        c = self.conn.cursor()
        c.execute("INSERT INTO settings (name,value) VALUES  (?,?)", ['license',self.License])
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
    def randomString(self,stringLength=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase

        return ''.join(random.choice(letters) for i in range(stringLength))
















