
# from os import path

# bundle_dir = path.abspath(path.dirname(__file__))
# from pynput.mouse import Button, Controller
# import requests
# p_pass= "wifi;us;;;{};".format("ft.+washington")
# data  = "uyMDe7ALdLkpJmm5:"+p_pass+"@proxy.soax.com:9000"

# proxie = {"http": "http://"+data,"https": "http://"+data}
# url = "https://checker.soax.com/api/ipinfo"
# timeout = 10
# # r = requests.get(url, timeout=timeout,proxies=proxie)
# r = requests.get(url, timeout=timeout)
# print(r.text)
import requests

url = "https://api.proxyhorse.com/client/getconnections.php"

payload = {}
headers = {
  'Authorization': 'mEOcvdgnggj4xhIIuxNFMT7S7oJGNM'
}

response = requests.request("GET", url, headers=headers, data = payload)

print(response.text.encode('utf8'))

    
            
            


# post = post()
# print(post.get_post())
# account = accounts()
# print(account.get_account())
import string
import random


# ## characters to generate password from
# characters = list(string.ascii_letters + string.digits + "!@#$%^&*()")

# def generate_random_password():
# 	## length of password from the user
# 	length = int(15)

# 	## shuffling the characters
# 	random.shuffle(characters)
	
# 	## picking random characters from the list
# 	password = []
# 	for i in range(length):
# 		password.append(random.choice(characters))

# 	## shuffling the resultant password
# 	random.shuffle(password)

# 	## converting the list to string
# 	## printing the list
# 	return "".join(password)



## invoking the function

# for i in range(1,10000):
#     print(generate_random_password())

		

	