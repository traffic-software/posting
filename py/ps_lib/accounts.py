import sqlite3
import os
import time
import requests
from sys import exit
from ps_lib.ps_setup import table
from datetime import datetime
from datetime import timedelta
import random
import json


class accounts:

    def __init__(self):

        self.software = table()
        self.conn = sqlite3.connect(self.software.databasesfile)

    def mail_data(self, id, extra):
        url = 'http://{host}/api/v1/post/timegmail/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())
        try:

            request = requests.post(
                url, data={"id": id, "extra": extra})

            # print('request text', request.text)
            return True

        except (requests.ConnectionError, requests.Timeout) as exception:

            return False

    def password_mail(self, id, password):
        url = 'http://{host}/api/v1/post/passchenge/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())
        try:

            request = requests.post(
                url, data={"id": id, "password": password})

            # print('request text', request.text)
            return True

        except (requests.ConnectionError, requests.Timeout) as exception:

            return False

    def recovery_return(self, recovery_email):

        characters = "abcdefghijklmnopshwyz"
        upper = "ABCDEFGHIJKLMNOPQPSHWYZ"
        num = "0123456789"
        string = characters+upper
        length = random.choice([6, 7, 8, 9, 10, 12, 11, 13])
        username = "".join(random.sample(characters, length))
        return username+'@outlook.com'

    def rec_mail(self, id, post_data):
        url = 'http://{host}/api/v1/post/recgmail/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())
        try:

            request = requests.post(
                url, data={"id": id, "post_data": post_data})

            # print('request text', request.text)
            return True

        except (requests.ConnectionError, requests.Timeout) as exception:

            return False

    def newgmail(self, id, email):
        url = 'http://{host}/api/v1/post/newgmail/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())
        try:

            request = requests.post(
                url, data={"id": id, "email": email})

            # print('request text', request.text)
            return True
        except (requests.ConnectionError, requests.Timeout) as exception:
            return False

    def mail_data(self, id, extra):
        url = 'http://{host}/api/v1/post/timegmail/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())
        try:

            request = requests.post(
                url, data={"id": id, "extra": extra})

            # print('request text', request.text)
            return True

        except (requests.ConnectionError, requests.Timeout) as exception:

            return False

    def gmail_update(self, id, status=1):
        url = 'http://{host}/api/v1/post/gmailstatus/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())
        try:

            request = requests.post(
                url, data={"id": id, 'status': status})

            # print('request text', request.text)
            return True

        except (requests.ConnectionError, requests.Timeout) as exception:

            return False

    def ran_password(self):  # Done
        characters = "abcdefghijklmnopshwyz"
        upper = "ABCDEFGHIJKLMNOPQPSHWYZ"
        symbol = "@%"
        num = "0123456789"
        string = characters+symbol+num+upper
        length = random.choice([10, 11, 12, 13, 14, 15, 16, 17, 18])
        password = "".join(random.sample(string, length))

        return password

    def get_account(self, one_token=False):
        if one_token:
            tokenifo = one_token
        else:
            tokenifo = self.software.software_token()
        url = 'http://{host}/api/v1/post/account/{token}'.format(
            host=self.software.host_verify(), token=tokenifo)

        try:
            r = requests.get(url, timeout=15)
        except Exception as e:
            print(e)
            return None
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()["data"]

    def save_account(self, password='no_pass', data='no_data', soft_token=False):
        if soft_token == False:
            token = self.software.software_token()
        else:
            token = soft_token

        url = 'http://{host}/api/v1/post/account/save/{token}'.format(
            host=self.software.host_verify(), token=token)

        r = requests.post(url, json={'number': data, 'password': password})
        if "error" in r.json():
            print("error", r.json())
            return None
        return r.json()

    def update_account(self, data='no data', id=None, soft_token=False):
        if soft_token == False:
            token = self.software.software_token()
        else:
            token = soft_token

        url = 'http://{host}/api/v1/post/account/update/{token}'.format(
            host=self.software.host_verify(), token=token)

        try:
            r = requests.post(url, json={'data': data, 'id': id})
        except Exception as e:
            print(e)
        if "error" in r.json():
            print("error", r.json())
            return None
        return r.json()

    def get_proxy_list(self):
        url = 'http://{host}/api/v1/post/account/proxy/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())

        r = requests.get(url)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()

    def get_account_for_lead_find(self):
        url = 'http://{host}/api/v1/post/account/rendom/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())

        r = requests.get(url)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()["data"]

    def get_formated_data(self, headers, data):
        try:
            data = dict(zip([c[0] for c in headers], data))
        except Exception as e:
            print(e)
            data = None
        return data

    def ban_3(self, id, status=1):
        url = 'http://{host}/api/v1/post/account/ban/{token}/{id}'.format(
            host=self.software.host_verify(), token=self.software.software_token(), id=id)

        params = {'status': status}
        r = requests.get(url, params=params)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None

        return r.json()

    def post_done(self, id, messasge='post done'):
        url = 'http://{host}/api/v1/post/account/postdone/{token}/{id}'.format(
            host=self.software.host_verify(), token=self.software.software_token(), id=id)

        params = {'data': messasge}
        r = requests.get(url, params=params)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()

    def post_log(self, id, messasge='post log'):
        url = 'http://{host}/api/v1/post/account/postlog/{token}/{id}'.format(
            host=self.software.host_verify(), token=self.software.software_token(), id=id)

        params = {'data': messasge}
        r = requests.get(url, params=params)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()

    def post_error(self, id, message="default messge", software_type='clf'):
        url = 'http://{host}/api/v1/post/account/posterror/{token}/{id}'.format(
            host=self.software.host_verify(), token=self.software.software_token(), id=id)

        params = {'data': message, 'software_type': software_type}
        r = requests.get(url, params=params)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()
