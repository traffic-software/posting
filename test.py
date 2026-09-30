
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from ps_lib.uc import ucbrowser
from ps_lib.accounts import accounts
# acc = accounts()
# account_data=acc.get_account()
# for x in range(0, 5):

#     # if account_data['extra'][0:1]==0:
        
        
#     print(00+int(account_data['extra'])-x)
#     print('................{0}..............'.format(x))

bundle_dir = os.path.abspath(os.path.dirname(__file__))


class Main:
    def __init__(self):
        self.url = 'https://accounts.google.com/ServiceLogin'
        one_account=234
        profile_dir=bundle_dir+"\{0}\{1}".format("profiles",str(one_account))
        if os.path.isdir(bundle_dir+"\{0}\{1}".format("profiles",str(one_account))) == False:
    
            profile_dir=bundle_dir+"\{0}\{1}".format("profiles",str(one_account))
        self.driver = ucbrowser(one_account,use_proxy=True, headless=False,profile_dir=profile_dir,image_bock=False)
        self.time = 6000

    def login(self, email, password):
        self.driver.get_url(self.url)
        

        self.code()

    def code(self):
        # [ ---------- paste your code here ---------- ]
        time.sleep(self.time)


if __name__ == "__main__":
    import re
    rtcExtensiion= line = re.sub(r"\d+", "", 'http://pubproxy.com/api/proxy?&format=json&https=true&type=https&contry=IT/485785')
    print(rtcExtensiion)
    #  ---------- EDIT ----------
    email = '1706973461'  # replace email
    password = '1706973461'  # replace password
    #  ---------- EDIT ----------

    driver = Main()
    driver.login(email, password)
# from os import path

# bundle_dir = path.abspath(path.dirname(__file__))
# from pynput.mouse import Button, Controller
# from itertools import count
# import json
# from numpy import number
# import requests
# from ps_lib.proxy import ps_proxy
# import string
# import random
# import os
# bundle_dir = os.path.abspath(os.path.dirname(__file__))
# print(bundle_dir)
# print(os.path.dirname(os.path.abspath(__file__))+"\manifest.zip")

# url = "https://geo.craigslist.org"
# timeout = 10
# proxie = {"http": "http://932eba933076a67fc7ee3b4a29664b52:f02769a4fcbcb32d1d436ad3da91b227@199.189.86.111:9500",
#           "https": "http://932eba933076a67fc7ee3b4a29664b52:f02769a4fcbcb32d1d436ad3da91b227@199.189.86.111:9500"}
# r = requests.get(url, proxies=proxie)
# print(r.status_code)
# print(r.text)


# def proxy_check(data):
#     try:
#         d = "{}:{}@{}:{}".format(data['user'],
#                                  data['password'], data['ip'], data['port'])
#         proxie = {"http": "http://"+d, "https": "http://"+d}
#         # if data['type'] == 'nouser':
#         # proxie = {"http": "http://"+data, "https": "http://"+data}

#         url = "http://ip-api.com/json"
#         r = requests.get(url, timeout=10, proxies=proxie)

#         if r.status_code in [400, 407, 500, 502, 522, 525]:
#             print('status_code {0}'.format(r.status_code))

#             return r.status_code

#         ip = json.loads(r.text)
#         print(ip)

#         return ip

#     except Exception as e:
#         print(e)
# .............proxyrotator.com................


# proxy_check('103.47.66.154:8080')
# exit()
# url = 'http://falcon.proxyrotator.com:51337'
# params = dict(
#     apiKey='hEQPUdGan7BjCw4X8rtxkTzFMNYH392c',
#     userAgent='true',
#     country='US',
#     get='true',
#     # connectionType='Residential'
# )
# counter = 1
# while True:
#     counter = counter+1
#     print(counter)

#     resp = requests.get(url, params=params, timeout=3)

#     data = json.loads(resp.text)
#     data['user'] = '932eba933076a67fc7ee3b4a29664b52'
#     data['password'] = 'f02769a4fcbcb32d1d436ad3da91b227'
#     proxy_check(data)


# .............pubproxy.com......................
# url = 'http://pubproxy.com/api/proxy?&format=json&https=true&type=https&contry=IT'
