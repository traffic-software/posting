
from datetime import date
import json
from re import T
import random
import requests
from requests.exceptions import ProxyError
from ps_lib.ps_setup import table
from ps_lib.loction import s 
import os
import time


class ps_proxy:
    def __init__(self, company, key):
        self.t = table()
        self.company =company
        self.country = "US"
        self.state = ""
        self.city = ""
        self.asn = ""
        
        if self.company == "proxyhorse":
            
            self.api_key = key
        if self.company == "soax":
            k=key.split("-")
            
            self.api_key = k[0]
            self.package_key = k[1]

    def proxy_headers(self):
        return {'authorization': self.api_key, 'Content-Type': 'application/json'}
    def proxy_payload(self,token=False,type=None,country=True,state=True,city=True,asn=True):
        d = {}
        if  country:
            d["country"]=str(self.country)
        if  state:
            d["state"]=str(self.state)
        if  city:
            d["city"]=str(self.city)
        if asn:
            d["asn"]= str(self.asn)
        if token:
            d['token'] = token
        if type==0:
            d={}
        return d
   
    def proxysoax(self,location):
        proxy_loction = location.split("-")
        self.state = proxy_loction[0].upper()
        self.city = proxy_loction[1].lower()
        check_city=self.get_soax_city(self.city)

        if  check_city== False:
            print(self.city,"city not available")
            return False
        else:
            returndata = False
            p = "wifi;us;;;{};".format(check_city)
            proxy = {}
            proxy['login'] = self.package_key
            proxy['password'] = p
            proxy['ip'] = "proxy.soax.com"
            proxy['port'] = 9000
            if False == self.proxy_check(data=proxy):
                print("proxy not have in city try to new city")

                newcity = self.get_soax_city_by_state(self.get_soax_state())
                p = "wifi;us;;;{};".format(newcity)
                proxy['password'] = p
                if self.proxy_check(data=proxy):
                    returndata =p
                else:
                    return False
            else:
                returndata =p
            
            return returndata

            
           

        
        
        
    def get_soax_city(self,city):
        d=False
        url = "https://soax.com/api/get-country-cities?api_key={0}&package_key={1}&country_iso=us&conn_type=wifi".format(self.api_key,self.package_key)
        response = requests.get(url,headers=self.proxy_headers(), data=json.dumps(self.proxy_payload(type=0)))
        t = json.loads(response.text.encode('utf8'))
        for i in t:
            
            if city == i:
                print(city,i)
                d = i
                break
        return d
    
    def get_soax_city_by_state(self,state):
        url = "https://soax.com/api/get-country-cities?api_key={0}&package_key={1}&country_iso=us&conn_type=wifi&region={2}".format(self.api_key,self.package_key,state)
        response = requests.get(url,headers=self.proxy_headers(), data=json.dumps(self.proxy_payload(type=0)))
        t = json.loads(response.text.encode('utf8'))
        d=random.choice(t)
        return d
    
    def get_soax_state(self):
        n = None
        for i in s:
            if self.state == i['av']:
                n = i['name']
                break
        return n
    

    def proxyhorse(self,location):
        proxy_loction = location.split("-")
        self.state = proxy_loction[0]
        self.city = proxy_loction[1]
        self.set_city(proxy_loction[1])
        
        
        token = self.t.proxyhorse_get()
        
        if token:
           new_proxy = self.change(token=token)
        else:
            new_proxy = self.new_connection()
        return new_proxy
        
    

    def new_connection(self):
        #new connection
        url = "https://api.proxyhorse.com/client/createconnection.php"
        r = requests.request("POST", url, headers=self.proxy_headers(), data=json.dumps(self.proxy_payload()))
        d =json.loads(r.text.encode('utf8'))
        self.t.proxyhorse_save(token=d['data']['token'])
        print("new_connection set location")
        
        if False == self.proxy_check(d['data']):
            print("post city probolem")
            time.sleep(30)
            exit()

            
            
        return d['data']
    #retun proxy info
    def change(self,token):
        url = "https://api.proxyhorse.com/client/changeconnection.php"
        
        r = requests.post(url, headers=self.proxy_headers(), data=json.dumps(self.proxy_payload(token)))
        d = json.loads(r.text.encode('utf8'))
        print("Change location")
        proxy = self.get_connecton(token=token)
        
        if False == self.proxy_check(proxy):
            print("post city probolem")
            time.sleep(30)
            exit()
        
        return proxy
    def delete(self,token):
        url = "https://api.proxyhorse.com/client/deleteconnection.php"
        r = requests.delete(url, headers=self.proxy_headers(), data=json.dumps(self.proxy_payload(token)))
       
    def get_connecton(self,token=False):
        d = False
        if token == False:
            token = self.t.proxyhorse_get()
            
        
        if token:
            url = "https://api.proxyhorse.com/client/getconnections.php"
            response = requests.get(url,headers=self.proxy_headers(), data=json.dumps(self.proxy_payload(type=0)))
            t = json.loads(response.text.encode('utf8'))
            for i in t['data']:
                if token == i['token']:
                    
                    d = i
                    break
        return d

    
        
    def set_city(self,city):
        url = "https://api.proxyhorse.com/client/getlocations.php"
        response = requests.get(url,headers=self.proxy_headers(), data=json.dumps(self.proxy_payload(city=False,asn=False)))
        t = json.loads(response.text.encode('utf8'))
        ip = t['data']
        ct=True
        try:
            for c in ip:
                if city == c['city_name']:
                    self.city = c['city_name']
                    ct=False
                    break
            
            if ct and len(ip):
                one_city= random.choice(ip)
                self.city = one_city['city_name']
            else:
                self.city=""
        except:
            self.city=""
            print('city problem')

        
        return self.city

        
    def get_ip(self,token=False):
        url = "https://api.proxyhorse.com/client/getconnectionip.php"
        response = requests.post(url,headers=self.proxy_headers(), data=json.dumps(self.proxy_payload(token=token)))
        t = json.loads(response.text.encode('utf8'))
        ip = t['data']
        
        if "United States" == ip['country'] and self.city == ip['city']:
            print("country:",ip['country'],"sate:",ip['state'],"city:",ip['city'])
            return True
        else:
            self.city=""
            return False

    def proxy_check(self,data):
        d  ="{}:{}@{}:{}".format(data['login'],data['password'],data['ip'],data['port'])
        proxie = {"http": "http://"+d,"https": "http://"+d}
        url = "http://ip-api.com/json"
        r = requests.get(url, timeout=10,proxies=proxie)
        if 'request_uuid' in r.text:
            self.city=""
            return False
        ip=json.loads(r.text)
        if "United States" in ip['country'] and self.state ==ip['region']:
            print("country:",ip['country'],"sate:",ip['region'],"city:",ip['city'])
            
            return True
        else:
            self.city=""
            return False