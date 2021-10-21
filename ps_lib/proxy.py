
import json

import requests
from ps_lib.ps_setup import table
import os
import time


class ps_proxy:
    def __init__(self, company, key):
        if company == "proxyhorse":
            self.api_key = key

    def proxyhorse(self,location):
        for i in self.get_all_proxy():
            print('\n',i)
            self.proxyhours_delete(i['token'])
        

        #new connection
        url = "https://api.proxyhorse.com/client/createconnection.php"
        proxy_loction = location.split("-")
        payload = {
		    "country": "US", 
			"state": proxy_loction[0], 
			"city": proxy_loction[1],
            "asn": ""
			}
        
       
        headers = {
		   	'Authorization': self.api_key,
			'Content-Type': 'application/json'
			}
        r = requests.request("POST", url, headers=headers, data=json.dumps(payload))
            
        new_proxy = json.loads(r.text.encode('utf8'))
            
        
        return new_proxy['data']
    def proxyhours_delete(self,token):
        url = "https://api.proxyhorse.com/client/deleteconnection.php"

        data = {"token": token}
        print(data)
        headers = {
        'authorization': self.api_key,
        'Content-Type': 'application/json'
        }

        response = requests.delete(url, headers=headers, data=json.dumps(data))
        print(response.text)
    def get_all_proxy(self):
        url = "https://api.proxyhorse.com/client/getconnections.php"

        payload = {}
        headers = {
        'Authorization': self.api_key
        }

        r = requests.request("GET", url, headers=headers, params = payload)
        d = json.loads(r.text.encode('utf8'))
        
        return d['data']