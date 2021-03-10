import threading
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime
from ps_lib.browser import browser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper
import random

#w = int(input('how much worker you need? '))
# worker = w + 1

def main(account_data,url):
	#show work start time
	print(datetime.now().strftime("%H:%M:%S"))
	# thread name
	account_id = threading.currentThread().getName()

	print(str(account_id) + "\t" + str(account_data))

	worker = psThread(account_id)
	b = browser(account_id)

	print(b.get_url(url))
	accept_button = b.select_element('div.modal-footer > button')
	accept_button.click()
	post_button = b.select_element('[data-href="/fe/main.php?page=post_insert"]')
	post_button.click()
	accept2_button = b.select_element('[name="subprocedi18"]')
	accept2_button.click()
	b.select_dropdown('[id = "categoria-ins"]',"31")
	ps_data = account_data.split(":")
	email = ps_data[0]
	age = ps_data[1]
	sub = 'subject'
	body = 'body'

	b_sub = b.select_element('[id="titolo-ins"]')
	b_sub.send_keys(sub)
	b_body = b.select_element('[id="testo-ins"]')
	b_body.send_keys(body)
	b_age = b.select_element('[id="eta-ins"]')
	b_age.send_keys(age)
	b_email = b.select_element('[name="email"]')
	b_email.send_keys(email)
	b_checkbox1 = b.select_element_xpath('//input[@id="privacy-ins"]')

	b.scroll_element_into_view(b_checkbox1)
	time.sleep(5)
	b_checkbox1.click()
	b.get_title()


	time.sleep(10)
	b.exit()

	print(datetime.now().strftime("%H:%M:%S"))








worker = 2
# ........................start worker....................
# ng-click="doLogin()"
mess1 = "how are you?"
mess2 = "where are you from"
mess3 = "Basically I don't use lovoo all the time, let's talk about it in the mail"
# driver.get("https://www.lovoo.com")
# driver.close()
open('active.txt', "w+")
utility = helper()
utility.all_account_active()
threads = []
headers = {}
profile_ids = {}
pid = threading.local()
urls = [
		'https://teramo.bakecaincontrii.com/donna-cerca-uomo',
		'https://terni.bakecaincontrii.com/donna-cerca-uomo',
		'https://torino.bakecaincontrii.com/donna-cerca-uomo',
		'https://trapani.bakecaincontrii.com/donna-cerca-uomo',
		'https://trento.bakecaincontrii.com/donna-cerca-uomo',
		'https://treviso.bakecaincontrii.com/donna-cerca-uomo',
		'https://trieste.bakecaincontrii.com/donna-cerca-uomo',
		'https://udine.bakecaincontrii.com/donna-cerca-uomo',
		'https://urbino.bakecaincontrii.com/donna-cerca-uomo',
		'https://varese.bakecaincontrii.com/donna-cerca-uomo',
		'https://venezia.bakecaincontrii.com/donna-cerca-uomo',
		'https://verbania.bakecaincontrii.com/donna-cerca-uomo',
		'https://vercelli.bakecaincontrii.com/donna-cerca-uomo',
		'https://verona.bakecaincontrii.com/donna-cerca-uomo',
		'https://vibovalentia.bakecaincontrii.com/donna-cerca-uomo',
		'https://vicenza.bakecaincontrii.com/donna-cerca-uomo',
		'https://viterbo.bakecaincontrii.com/donna-cerca-uomo',
	]


while True:
	acc = accounts()
	acc.save()

	if worker > threading.active_count():
		url = random.choice(urls)
		one_account = acc.get_account()
		if one_account == None:
			time.sleep(10)
			acc.get_account_for_inactive()

			continue
		acc.account_active(one_account[0])

		t = threading.Thread(target=main, args=(one_account[1],url,))
		acc.account_active(one_account[0])

		threads.append(t)
		t.setName(one_account[0])
		t.start()
		time.sleep(50)

	else:

		print('..............active thread :' + str(threading.active_count()) + '...............')
		time.sleep(50)
