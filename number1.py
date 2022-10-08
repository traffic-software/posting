import json
import requests
import time

import countrys


class number:
    token = ''
    country = 0
    country_c = '+1'
    operator = 0
    product = 0
    num_id = 0
    number = None
    count_code = 0
    active_code = False

    def __init__(self, token, country, operator, product):
        self.token = token
        self.country = country
        self.country_c = '+1'
        self.operator = operator
        self.product = product

    def buy_number(self):
        if self.number == None:

            headers = {
                'Authorization': 'Bearer ' + self.token,
                'Accept': 'application/json',
            }

            for i in range(1, 60):

                url = 'https://5sim.net/v1/user/buy/activation/{0}/{1}/{2}'.format(
                    str(self.country), str(self.operator), str(self.product))
                # print(url)

                r = requests.get(url, headers=headers)
                print(r.status_code)
                if r.status_code != 200:
                    time.sleep(10)
                    print(r.text)

                    continue
                if 'id' in r.text:
                    r = r.json()
                    self.country_c = countrys.codes(self.country)
                    print(self.country_c)
                    newNumber = r["phone"].replace(self.country_c, '')

                    oder_no = r['id']

                    self.num_id = oder_no
                    self.number = newNumber
                    return self.number
                    break
                else:
                    print(r.text)
                    time.sleep(10)
                    print('Waiting for number')
        else:
            return self.number

    def check_sms(self):

        id = self.num_id

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/json',
        }
        code = False
        for i in range(1, 15):

            r = requests.get(
                'https://5sim.net/v1/user/check/' + str(id), headers=headers)

            if (r.status_code == 200) and (len(r.json()['sms']) >= 1):

                data = r.json()['sms'][-1]
                print(data)
                code = data["code"]

                self.count_code = self.count_code+1

                if self.active_code != code:
                    self.active_code = code
                    break

            print("waiting for sms")
            time.sleep(10)
        if self.active_code == False:
            print('self.active_code == False')
            self.ban_number()

        return code

    def ban_number(self):
        print('ban number')
        self.number = None
        self.country_c = '+1'
        self.count_code = 0
        if self.active_code:
            return None

        id = self.num_id

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/json',
        }
        time.sleep(1)

        response = requests.get(
            'https://5sim.net/v1/user/ban/' + str(id), headers=headers)
        self.num_id = 0
        print(response.text)

    def finish_number(self):

        id = self.num_id

        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/json',
        }

        r = requests.get('https://5sim.net/v1/user/finish/' +
                         id, headers=headers)

    def get_prices(product='google'):
        product = 'google'
        time.sleep(1)

        headers = {
            'Accept': 'application/json',
        }

        params = (
            ('product', product),
        )
        response = requests.get(
            'https://5sim.net/v1/guest/prices', headers=headers, params=params)
        items = response.json()[product]
        for i in items:
            fastitem = next(iter(items[i].values()))
            fastitem['country'] = i
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
