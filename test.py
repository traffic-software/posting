<<<<<<< HEAD

from datetime import date
import json
from re import T
import random
import requests
from requests import exceptions
from requests.exceptions import ProxyError
from ps_lib.ps_setup import table
from ps_lib.accounts import accounts
from ps_lib.loction import s
import os
import time


class ps_proxy:
    def __init__(self, company, key):
        self.t = table()
        self.pva = accounts()
        self.company = company
        self.country = "US"
        self.state = ""
        self.city = ""
        self.asn = ""
        self.pva_id = None

        if self.company == "proxyhorse":

            self.api_key = key
        if self.company == "soax":
            k = key.split("-")

            self.api_key = k[0]
            self.package_key = k[1]

    def proxy_headers(self):
        return {'authorization': self.api_key, 'Content-Type': 'application/json'}

    def proxy_payload(self, token=False, type=None, country=True, state=True, city=True, asn=True):
        d = {}
        if country:
            d["country"] = str(self.country).upper()
        if state:
            s = str(self.state)
            d["state"] = s.upper()
        if city:
            c = str(self.city)
            d["city"] = c.title()
        if asn:
            d["asn"] = str(self.asn)
        if token:
            d['token'] = token
        if type == 0:
            d = {}

        return d

    def proxysoax(self, location):
        proxy_loction = location.split("-")
        self.state = proxy_loction[0].upper()
        self.city = proxy_loction[1].lower()
        returndata = False
        p = "wifi;us;;;{};".format(self.city.replace(' ', '+'))
        proxy = {}
        proxy['login'] = self.package_key
        proxy['password'] = p
        proxy['ip'] = "proxy.soax.com"
        proxy['port'] = random.randrange(9000, 9299)
        if self.proxy_city_check(data=proxy, city=self.city):
            returndata = proxy

        state = self.get_soax_state()
        p = "wifi;us;;{};;".format(state.replace(' ', '+'))
        proxy['password'] = p
        if self.proxy_check(data=proxy):
            returndata = proxy

        return returndata

    def get_soax_state(self):
        n = None
        for i in s:

            if self.state.upper() == i['av'].upper():
                n = i['name'].lower()
                break
        return n

    def proxyhorse(self, location="any-any", pva_id=None):
        proxy_loction = location.split("-")
        self.state = proxy_loction[0]
        self.city = proxy_loction[1]
        # self.set_city(proxy_loction[1])
        self.pva_id = pva_id

        token = self.t.proxyhorse_get()

        if token:
            new_proxy = self.change(token=token)
        else:
            new_proxy = self.new_connection()
        return new_proxy

    def new_connection(self):
        # new connection
        url = "https://api.proxyhorse.com/client/createconnection.php"
        r = requests.request("POST", url, headers=self.proxy_headers(
        ), data=json.dumps(self.proxy_payload()))
        d = json.loads(r.text.encode('utf8'))

        self.t.proxyhorse_save(token=d['data']['token'])
        print("new_connection set location")
        proxy = d['data']
        self.get_ip(proxy['token'])

        return proxy
    # retun proxy info

    def change(self, token):
        url = "https://api.proxyhorse.com/client/changeconnection.php"

        payload = self.proxy_payload(token=token)
        print('change payload', payload)

        r = requests.post(url, headers=self.proxy_headers(),
                          data=json.dumps(payload))
        d = json.loads(r.text.encode('utf8'))
        print(d)
        print("Change location")
        proxy = self.get_connecton(token=token)

        self.get_ip(proxy['token'])

        return proxy

    def delete(self, token):
        url = "https://api.proxyhorse.com/client/deleteconnection.php"
        payload = self.proxy_payload(token=token)
        print('delete payload', payload)
        r = requests.delete(url, headers=self.proxy_headers(),
                            data=json.dumps(payload))

    def get_connecton(self, token=False):
        d = False
        if token == False:
            token = self.t.proxyhorse_get()

        if token:
            url = "https://api.proxyhorse.com/client/getconnections.php"
            payload = {'token': token}
            print('get_connecton payload', payload)
            response = requests.get(url, headers=self.proxy_headers(
            ), data=json.dumps(payload))
            t = json.loads(response.text.encode('utf8'))

            for i in t['data']:
                if token == i['token']:

                    d = i
                    break

        return d

    def set_city(self, city):
        url = "https://api.proxyhorse.com/client/getlocations.php"
        payload = self.proxy_payload(city=False, asn=False)
        print('set_city payload', payload)
        response = requests.get(url, headers=self.proxy_headers(
        ), data=json.dumps(payload))
        t = json.loads(response.text.encode('utf8'))
        ip = t['data']
        print(ip)

        ct = True
        try:
            for c in ip:

                if (city.title() == c['city_name'].title()):
                    self.city = c['city_name'].title()
                    print('city find ', self.city)

                    ct = False
                    break

            if ct:

                one_city = random.choice(ip)
                self.city = one_city['city_name'].title()
                print('rendom city ', self.city)

        except:
            self.city = ""
            print('city problem')
        print(self.city)
        return self.city

    def get_ip(self, token=False):
        url = "https://api.proxyhorse.com/client/getconnectionip.php"
        payload = {'token': token}
        print('get_ip payload', payload)
        response = requests.post(url, headers=self.proxy_headers(
        ), data=json.dumps(payload))
        t = json.loads(response.text.encode('utf8'))
        print(t)
        ip = t['data']

        if "United States" == ip['country'] and self.city == ip['city']:
            print("country:", ip['country'], "sate:",
                  ip['state'], "city:", ip['city'])
            return True
        else:
            self.city = ""
            return False

    def proxy_check(self, data):
        try:
            d = "{}:{}@{}:{}".format(data['login'],
                                     data['password'], data['ip'], data['port'])
            proxie = {"http": "http://"+d, "https": "http://"+d}
            url = "http://ip-api.com/json"
            r = requests.get(url, timeout=10, proxies=proxie)

            if 'request_uuid' in r.text:
                print(r.text)
                self.city = ""
                return False
            ip = json.loads(r.text)
            print('proxy_check', self.state)

            if "United States".lower() in ip['country'].lower() and self.state.lower() == ip['region'].lower():
                print("country:", ip['country'], "sate:",
                      ip['region'], "city:", ip['city'])

                return True
            else:
                self.city = ""

                return False
        except Exception as e:
            print(e)
            return False

    def proxy_city_check(self, data, city):
        try:
            d = "{}:{}@{}:{}".format(data['login'],
                                     data['password'], data['ip'], data['port'])
            proxie = {"http": "http://"+d, "https": "http://"+d}
            url = "http://ip-api.com/json"
            r = requests.get(url, timeout=10, proxies=proxie)
=======
# from selenium import webdriver

# options = webdriver.ChromeOptions()
# options.add_experimental_option("useAutomationExtension", False)
# options.add_experimental_option("excludeSwitches",["enable-automation"])

# driver_path = 'chromedriver.exe'
# driver = webdriver.Chrome(executable_path=driver_path, chrome_options=options)
# driver.get('https://google.com')

# driver.close()
# from os import path

# bundle_dir = path.abspath(path.dirname(__file__))
# from pynput.mouse import Button, Controller
from itertools import count
import json
from numpy import number
import requests
# from ps_lib.proxy import ps_proxy
import string
import random
import os


# url = "https://geo.craigslist.org"
# timeout = 10
# proxie = {"http": "http://932eba933076a67fc7ee3b4a29664b52:f02769a4fcbcb32d1d436ad3da91b227@199.189.86.111:9500",
#           "https": "http://932eba933076a67fc7ee3b4a29664b52:f02769a4fcbcb32d1d436ad3da91b227@199.189.86.111:9500"}
# r = requests.get(url, proxies=proxie)
# print(r.status_code)
# print(r.text)
def proxy_check(data):
    try:
        d = "{}:{}@{}:{}".format(data['user'],
                                 data['password'], data['ip'], data['port'])
        proxie = {"http": "http://"+d, "https": "http://"+d}
        # if data['type'] == 'nouser':
        # proxie = {"http": "http://"+data, "https": "http://"+data}

        url = "http://ip-api.com/json"
        r = requests.get(url, timeout=10, proxies=proxie)

        if r.status_code in [400, 407, 500, 502, 522, 525]:
            print('status_code {0}'.format(r.status_code))

            return r.status_code

        ip = json.loads(r.text)
        print(ip)

        return ip

    except Exception as e:
        print(e)
# .............proxyrotator.com................
>>>>>>> cl

            if 'request_uuid' in r.text:
                print(r.text)
                self.city = ""
                return False
            ip = json.loads(r.text)
            print('proxy_check city ', self.city)
            print(ip)

<<<<<<< HEAD
            if "United States".lower() in ip['country'].lower() and city.lower() == ip['city'].lower():
                print("country:", ip['country'], "sate:",
                      ip['region'], "city:", ip['city'])

                return True
            else:
                self.city = ""

                return False
        except Exception as e:
            print(e)
            return False


psproxy = ps_proxy(company="soax", key='HzoxSzpE1Y_zJf5Y-uyMDe7ALdLkpJmm5')
print(psproxy.proxysoax('NJ-Jersey Shore'))
=======
# proxy_check('103.47.66.154:8080')
# exit()
url = 'http://falcon.proxyrotator.com:51337'
params = dict(
    apiKey='hEQPUdGan7BjCw4X8rtxkTzFMNYH392c',
    userAgent='true',
    country='US',
    get='true',
    # connectionType='Residential'
)
counter = 1
while True:
    counter = counter+1
    print(counter)

    resp = requests.get(url, params=params, timeout=3)

    data = json.loads(resp.text)
    data['user'] = '932eba933076a67fc7ee3b4a29664b52'
    data['password'] = 'f02769a4fcbcb32d1d436ad3da91b227'
    proxy_check(data)


# .............pubproxy.com......................
# url = 'http://pubproxy.com/api/proxy?&format=json&https=true&type=https&contry=IT'
>>>>>>> cl
