import sqlite3
import os
import time
import requests
from sys import exit
from ps_lib.ps_setup import table
from datetime import datetime
from datetime import timedelta


class accounts:

    def __init__(self):

        self.software = table()
        self.conn = sqlite3.connect(self.software.databasesfile)

    def get_account(self):
        url = 'https://{host}/api/v1/post/account/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())

        r = requests.get(url)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()["data"]

    def get_proxy_list(self):
        url = 'https://{host}/api/v1/post/account/proxy/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())

        r = requests.get(url)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()

    def get_account_for_lead_find(self):
        url = 'https://{host}/api/v1/post/account/rendom/{token}'.format(
            host=self.software.host_verify(), token=self.software.software_token())

        r = requests.get(url)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()["data"]

    def get_formated_data(self, headers, data):
        try:
            data = dict(zip([c[0] for c in headers], data))
        except:
            data = None
        return data

    def ban_3(self, id, status=1):
        url = 'https://{host}/api/v1/post/account/ban/{token}/{id}'.format(
            host=self.software.host_verify(), token=self.software.software_token(), id=id)

        params = {'status': status}
        r = requests.get(url, params=params)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None

        return r.json()

    def post_done(self, id, messasge='post done'):
        url = 'https://{host}/api/v1/post/account/postdone/{token}/{id}'.format(
            host=self.software.host_verify(), token=self.software.software_token(), id=id)

        params = {'data': messasge}
        r = requests.get(url, params=params)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()

    def post_log(self, id, messasge='post log'):
        url = 'https://{host}/api/v1/post/account/postlog/{token}/{id}'.format(
            host=self.software.host_verify(), token=self.software.software_token(), id=id)

        params = {'data': messasge}
        r = requests.get(url, params=params)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()

    def post_error(self, id, message="default messge", software_type='clf'):
        url = 'https://{host}/api/v1/post/account/posterror/{token}/{id}'.format(
            host=self.software.host_verify(), token=self.software.software_token(), id=id)

        params = {'data': message, 'software_type': software_type}
        r = requests.get(url, params=params)
        if "error" in r.json():
            print("error", r.json()['message'])
            return None
        return r.json()
