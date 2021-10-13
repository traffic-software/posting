
# from os import path

# bundle_dir = path.abspath(path.dirname(__file__))
# from pynput.mouse import Button, Controller

import requests
proxy = {
    "http": "http://uyMDe7ALdLkpJmm5:wifi;us;;;los+angeles@proxy.soax.com:9000",
    "https": "http://uyMDe7ALdLkpJmm5:wifi;us;;;los+angeles@proxy.soax.com:9000"
}


resp = requests.get("http://checker.soax.com/api/ipinfo",proxies=proxy)

print(resp.text)

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

		

	