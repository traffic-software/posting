from itertools import count
import json
import requests
import string
import random
[
    {
    'domain': '.linkedin.com',
 'expiry': 1661095827,
  'httpOnly': False,
   'name': 'lidc',
    'path': '/',
     'sameSite': 'None',
      'secure': True,
       'value': '"b=TB41:s=T:r=T:a=T:p=T:g=3507:u=1:x=1:i=1661080956:t=1661095827:v=2:sig=AQHYS6qFjVq2KQcmcZRTy4wxSF81acIE"'
},
 {'domain': '.linkedin.com', 'expiry': 1663672898, 'httpOnly': False, 'name': 'lms_ads', 'path': '/', 'sameSite': 'None', 'secure': True, 'value': 'AQFrrvb6EhuhkgAAAYLAIw98-KjflGVFLwinKWiUdL1UXtnECrcskayBwKh1zDjl-0gqpwWqdP7OcQWgjyoq2BLTdFis7LFI'},
 {'domain': '.linkedin.com', 'expiry': 1663672955, 'httpOnly': False, 'name': 'UserMatchHistory', 'path': '/', 'sameSite': 'None', 'secure': True, 'value': 'AQIFYYjYXBnrwAAAAYLAI-wXseX5E1NBv_iwfAs8A8xIAnOr8HZd27p-AlZzXQwWpK8MJQUHlIry8VzYAZ8WsQUs559fLMcJN3_QhHhXRhdENx1ADFH5cfU0ypKRG_KCIffPnHJpFWIGG680mi9ZoGjvvRpNTrrHPt4f5Sft0IXtxUZhSxbSGV52FLAOPCHLi0jisLdWL4V_ajFs_DzRWdnCKwBrj08tQpI-JhLzczt5xnI14UjPrvdCNH5VhQBpZNBamvni-Wgo2NZwYHb7RWLvt4uQ1HlDNH85sOI'}, {'domain': '.linkedin.com', 'expiry': 1663672898, 'httpOnly': False, 'name': 'AnalyticsSyncHistory', 'path': '/', 'sameSite': 'None', 'secure': True, 'value': 'AQIC4XYGQGiyhwAAAYLAIw5qUILJoG8uNKbdVunqfT42TRaDF3VAqRHUqv1VQE8j6xknSULZ4-QYNo2uTKVEgQ'}, {'domain': '.linkedin.com', 'expiry': 1668856898, 'httpOnly': False, 'name': '_guid', 'path': '/', 'sameSite': 'None', 'secure': True, 'value': '8254fe70-effe-4b10-aa03-3744f9eaadc7'}, {'domain': '.linkedin.com', 'expiry': 1668856955, 'httpOnly': False, 'name': 'li_sugr', 'path': '/', 'sameSite': 'None', 'secure': True, 'value': 'bbf677c5-ef2f-4a96-8249-d3d0d9926083'}, {'domain': '.www.linkedin.com', 'expiry': 1692616890, 'httpOnly': True, 'name': 'bscookie', 'path': '/', 'sameSite': 'None', 'secure': True, 'value': '"v=1&20220821112130d9c128ae-065d-42ce-8fff-df2de5bb8d58AQHbmvBuF7AmPoZ2e7Kalf-RuDbbYYrS"'
 }
 ]
 print('hello worker'.title().replace(' ', ''))
# from ps_lib.proxy import ps_proxy

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
