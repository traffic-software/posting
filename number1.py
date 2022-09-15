import json
import requests
import time

import countrys


class number:
	token = 'eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjY0MzYwOTEsImlhdCI6MTYzNDkwMDA5MSwicmF5IjoiY2MzNzRmNTM3MTUyMDc3MWZjODAyNWM1MTM5OWIzYWUiLCJzdWIiOjIzMTAyOH0.OOd17iPERjvtNLc6KNa15nnG5hKXvkzeBf7aJa0ApMjWoO9on4NMC4UIbJRgJ8CtVk2dk7mVi5JwzC1e_zZXis-M2sx1GsFRgWum7BIlyxhYWYYp2rAJuW7YrcAn5MWBXC7E2DaKeeVonDgwzN1_FlUAEnS1iggGgdeKtTy3YZ75mH1z3lrsjjbml_vvP2PrCdpjEl7x2EXBizng3NNxqG72rF9OwI8I5mJj1ks0oHbdMNqOdScdExG6a9MJj9NXOFQmBx9C9bTgCCkhcd1T5bmX5-royaHq8LEyZnuE9HXMwo3mHL_Nny3mwCwftC95dMUqNARrQkY5p0hK4OUQfg'
	country = 0
	country_c = '+1'
	operator = 0
	product = 0
	num_id = 0

	def __init__(self, token, country, operator, product):
		self.token = token
		self.country = country
		self.country_c = '+1'
		self.operator = operator
		self.product = product

	def buy_number(self):

		headers = {
			'Authorization': 'Bearer ' + self.token,
			'Accept': 'application/json',
		}

		for i in range(1,60):
			
			url = 'https://5sim.net/v1/user/buy/activation/' + self.country +'/' + self.operator + '/' + self.product
			# print(url)


			r = requests.get(url, headers=headers)
			print(r.status_code)
			if r.status_code != 200:
				time.sleep(10)
				print(r.text)
				
				continue
			if 'id' in r.text:
				r = r.json()
				self.country_c =countrys.codes(self.country)
				print(self.country_c)
				number= r["phone"].replace(self.country_c,'')
    
				num_id = r['id']
				
				self.num_id = num_id
				return number
				break
			else:
				print(r.text)
				time.sleep(10)
				print('Waiting for number')

	
	def check_sms(self):
		
		
		id = self.num_id

		headers = {
			'Authorization': 'Bearer ' + self.token,
			'Accept': 'application/json',
		}
		code = False
		for i in range(1,30):
			r = requests.get('https://5sim.net/v1/user/check/' + str(id), headers=headers)
			if (r.status_code == 200) and (len(r.json()['sms'])>=1):

				data=r.json()['sms'][-1]
				print(data)
				code= data["code"]
				break
			time.sleep(10)
			print("waiting for sms")
		if code == False:
			self.ban_number()
		return  code
	
	def ban_number(self):

		id = self.num_id

		headers = {
			'Authorization': 'Bearer ' + self.token,
			'Accept': 'application/json',
		}
		time.sleep(1)

		response = requests.get('https://5sim.net/v1/user/ban/' + str(id), headers=headers)
		print(response.text)

	def get_prices(product = 'google'):
		product = 'google'
		time.sleep(1)

		headers = {
			'Accept': 'application/json',
		}

		params = (
			('product', product),
		)
		response = requests.get('https://5sim.net/v1/guest/prices', headers=headers, params=params)
		items = response.json()[product]
		for i in items:
			fastitem = next(iter(items[i].values()))
			fastitem['country']=i
			print(fastitem)
			print('.............................')

# object = number('eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjY0MzYwOTEsImlhdCI6MTYzNDkwMDA5MSwicmF5IjoiY2MzNzRmNTM3MTUyMDc3MWZjODAyNWM1MTM5OWIzYWUiLCJzdWIiOjIzMTAyOH0.OOd17iPERjvtNLc6KNa15nnG5hKXvkzeBf7aJa0ApMjWoO9on4NMC4UIbJRgJ8CtVk2dk7mVi5JwzC1e_zZXis-M2sx1GsFRgWum7BIlyxhYWYYp2rAJuW7YrcAn5MWBXC7E2DaKeeVonDgwzN1_FlUAEnS1iggGgdeKtTy3YZ75mH1z3lrsjjbml_vvP2PrCdpjEl7x2EXBizng3NNxqG72rF9OwI8I5mJj1ks0oHbdMNqOdScdExG6a9MJj9NXOFQmBx9C9bTgCCkhcd1T5bmX5-royaHq8LEyZnuE9HXMwo3mHL_Nny3mwCwftC95dMUqNARrQkY5p0hK4OUQfg','russia','any','aol')

# buy_number = object.buy_number()
# country_code = object.country_c
# print(buy_number)
# user = input(" ples type y")
# if user =="y":
# 	check_sms = object.check_sms()
# 	print(check_sms)