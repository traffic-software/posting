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
import random
import string
from ps_lib.proxy import ps_proxy
import requests
import json
url = "http://ip-api.com/json"
timeout = 10
# r = requests.get(url, timeout=timeout)
# if "zip" in r.text:
#     ip = json.loads(r.text)
#     return ip['zip']


# p_pass= "wifi;us;;;{};".format("ft.+washington")
# data  = "uyMDe7ALdLkpJmm5:"+p_pass+"@proxy.soax.com:9000"

# proxie = {"http": "http://"+data,"https": "http://"+data}
# url = 'https://soax.com/api/get-country-cities?api_key=HzoxSzpE1Y_zJf5Y&package_key=uyMDe7ALdLkpJmm5&country_iso=us&conn_type=wifi&region=nevada'
# # https://soax.com/api/get-country-cities?api_key=<api_key>&package_key=<package_key>&country_iso=<country_iso>&conn_type=<conn_type>[&provider=<provider_name>[&region=<region_name>]]
# timeout = 10
# proxy_payload ={
#     'api_key':'HzoxSzpE1Y_zJf5Y',
#     'package_key':'uyMDe7ALdLkpJmm5',
#     'country_iso':'us',
#     'conn_type':'wifi'
# }
# r = requests.get(url, timeout=timeout,data=proxy_payload)
# # r = requests.get(url, timeout=timeout)
# print(r.text)


url = "https://api.proxyhorse.com/client/getconnections.php"

payload = {}
headers = {
    'Authorization': 'Zp1ybaCFsuhb9iPVet04tYuYjFQiHfakuUyT2oJeIeVcLcOOqJ'
}

response = requests.request("GET", url, headers=headers, data=payload)
d = json.loads(response.text.encode('utf8'))
print(d)

for i in d['data']:
    url = "https://api.proxyhorse.com/client/deleteconnection.php"

    payload = {"token": "{}".format(i['token'])}
    headers = {
        'authorization': 'Zp1ybaCFsuhb9iPVet04tYuYjFQiHfakuUyT2oJeIeVcLcOOqJ',
        'Content-Type': 'application/json'
    }

    response = requests.request(
        "DELETE", url, headers=headers, data=json.dumps(payload))
psproxy = ps_proxy(company="proxyhorse", key='mEOcvdgnggj4xhIIuxNFMT7S7oJGNM')

proxy = psproxy.proxyhorse('NC-Chinquapin')


# post = post()
# print(post.get_post())
# account = accounts()
# print(account.get_account())


# characters to generate password from
characters = list(string.ascii_letters + string.digits + "!@#$%^&*()")


def generate_random_password():
    # length of password from the user
    length = int(15)

    # shuffling the characters
    random.shuffle(characters)

    # picking random characters from the list
    password = []
    for i in range(length):
        password.append(random.choice(characters))

    # shuffling the resultant password
    random.shuffle(password)

    # converting the list to string
    # printing the list
    return "".join(password)


# invoking the function

# for i in range(1,10000):
#     print(generate_random_password())
