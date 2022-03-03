
import urllib.request
from datetime import date
import json
from re import T
import random
from weakref import proxy
import requests
from requests import exceptions
from requests.exceptions import ProxyError
from ps_lib.ps_setup import table
from ps_lib.accounts import accounts
from ps_lib.loction import s
import os
import time

import string


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
            return returndata

        state = self.get_soax_state()
        p = "wifi;us;;{};;".format(state.replace(' ', '+'))
        proxy['password'] = p
        if self.proxy_check(data=proxy):
            returndata = proxy

        return returndata

    def firstProxy(self, location, proxyinfo):
        proxy_loction = location.split("-")
        self.state = proxy_loction[0].upper()
        self.city = proxy_loction[1].lower()
        letters = string.ascii_lowercase
        city = "any"

        if proxyinfo['company'] == 'oxylabs':
            city = self.city.replace(' ', '_')
            session = ''.join(random.choice(letters) for i in range(10))

            user = 'customer-{user}-st-{country}-city-{city}-sessid-{session}'.format(
                user=proxyinfo['user'], country=self.get_oxylabs_state(self.state), city=city, session=session)
            proxyinfo['user'] = user
        if proxyinfo['company'] == 'soax':
            city = self.city
            password = "wifi;us;;;{};".format(self.city.replace(' ', '+'))
            proxyinfo['password'] = password
            proxyinfo['user'] = self.package_key
            proxyinfo['port'] = random.randrange(9000, 9299)

        return self.proxy_check(proxyinfo, city.title())

    def backupProxy(self, location, proxyinfo):
        proxy_loction = location.split("-")
        self.state = proxy_loction[0].upper()
        self.city = proxy_loction[1].lower()
        letters = string.ascii_lowercase
        city = "any"

        if proxyinfo['company'] == 'oxylabs':
            city = self.city.replace(' ', '_')
            session = ''.join(random.choice(letters) for i in range(10))

            user = 'customer-{user}-st-{country}-city-{city}-sessid-{session}'.format(
                user=proxyinfo['user'], country=self.get_oxylabs_state(self.state), city=city, session=session)
            proxyinfo['user'] = user
        if proxyinfo['company'] == 'soax':
            city = self.city
            password = "wifi;us;;;{};".format(self.city.replace(' ', '+'))
            proxyinfo['password'] = password
            proxyinfo['user'] = self.package_key
            proxyinfo['port'] = random.randrange(9000, 9299)

        return self.proxy_check(proxyinfo, city.title())

    def normalProxy(self, location, proxyinfo):
        proxy_loction = location.split("-")
        self.state = proxy_loction[0].upper()
        letters = string.ascii_lowercase

        state = self.get_soax_state()

        # use oxylabs proxy compnay
        if proxyinfo['company'] == 'oxylabs':
            session = ''.join(random.choice(letters) for i in range(10))
            user = 'customer-{user}-st-{country}-sessid-{session}'.format(
                user=proxyinfo['user'], country=self.get_oxylabs_state(self.state), session=session)
            print(user)

            proxyinfo['user'] = user

        # use soax proxy compnay
        if proxyinfo['company'] == 'soax':

            proxyinfo['password'] = "wifi;us;;{};;".format(
                state.replace(' ', '+'))
            proxyinfo['user'] = self.package_key
            proxyinfo['port'] = random.randrange(9000, 9299)

        return self.proxy_state_check(data=proxyinfo, state=state.lower())

    def proxy_check(self, data, city):
        try:
            d = "{}:{}@{}:{}".format(data['user'],
                                     data['password'], data['host'], data['port'])
            proxie = {"http": "http://"+d, "https": "http://"+d}

            url = "http://ip-api.com/json"
            r = requests.get(url, timeout=60, proxies=proxie)
            print(r.text)
            if r.status_code in [400, 407, 500, 502, 522, 525]:
                return data

            ip = json.loads(r.text)

            city = city.replace('_', ' ')
            print(city.lower(), ip['city'].lower())

            if (city.lower() == ip['city'].lower()) and (self.state.lower() == ip['region'].lower()):
                data['checkinfo'] = ip
            else:
                data['notproxy'] = r.text

            return data

        except Exception as e:
            print(e)
            return data

    def proxy_state_check(self, data, state):
        try:
            d = "{}:{}@{}:{}".format(data['user'],
                                     data['password'], data['host'], data['port'])
            proxie = {"http": "http://"+d, "https": "http://"+d}

            url = "http://ip-api.com/json"
            r = requests.get(url, timeout=60, proxies=proxie)
            print(r.text)
            if r.status_code in [400, 407, 500, 502, 522, 525]:
                return data

            ip = json.loads(r.text)

            print(self.state, ip['region'].lower())

            if (self.state.lower() == ip['region'].lower()) and (ip['countryCode'].lower() == 'us'):
                data['checkinfo'] = ip
            else:
                data['notproxy'] = r.text

            return data

        except Exception as e:
            print(e)
            return data

    def get_soax_state(self):
        n = None
        for i in s:

            if self.state.upper() == i['av'].upper():
                n = i['name'].lower()
                break
        return n

    def get_oxylabs_state(self, st):
        n = None
        for i in s:

            if st.upper() == i['av'].upper():
                n = 'us_'+i['name'].lower()
                n = n.replace(' ', '_')

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

    def proxy_city_check(self, data, city):
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
            print('proxy_check city ', self.city)

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


if __name__ == "__main__":
    a = accounts()
    proxyinfo = a.get_proxy_list()
    # check for use defaultProxy
    dProxy = proxyinfo['defaultProxy']

    defaultProxy = ps_proxy(company=dProxy['company'], key=dProxy['user'])
    proxyinfo = defaultProxy.firstProxy(
        location='us_new jersey', proxyinfo=dProxy)
    if proxyinfo:
        print('proxy find')
        print(proxyinfo)
    else:
        print('proxy not find')
        print(proxyinfo)
