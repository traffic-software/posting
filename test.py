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
import requests
# from ps_lib.proxy import ps_proxy
import string
import random
import os

url = "https://stackoverflow.com/questions/90178/make-a-div-fill-the-height-of-the-remaining-screen-space?rq=1"
timeout = 10
data = {
    "prompt": "Does Windows 11 need antivirus?",
    "temperature": 0.3,
    "max_tokens": 150,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0
}
r = requests.post(url)

with open("response1.html", "w") as f:
    f.write(r.text)
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
# # .............proxyrotator.com................


# # proxy_check('103.47.66.154:8080')
# # exit()
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
