import threading
from selenium.webdriver.common.keys import Keys
import time
import shutil
from os import path
from datetime import datetime
from ps_lib.browser import browser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.imap import imap
import random
from pynput.mouse import Button, Controller

# mouse = Controller()
# input('place Your mouse on the tuxler vpn IP change button then type any key in your keyboard')
# # Read pointer position
# x,y=mouse.position
# # Set pointer position
# mouse.position = (x,y)
# mouse.move(1,1)
# # Press and release
# mouse.press(Button.left)
# mouse.release(Button.left)

# Double click; this is different from pressing and releasing
# twice on macOS
# mouse.click(Button.left, 2)

# Scroll two steps down
# mouse.scroll(0, 2)
# b = browser('545')
#
# b.get_url('http://httpbin.org/get')
# exit()


def main(account_data,url,postinfo):
	#show work start time
	print(datetime.now().strftime("%H:%M:%S"))
	# thread name
	account_id = threading.currentThread().getName()


	worker = psThread(account_id)
	b = browser(account_id)
	worker_acc=accounts()

	b.get_url(url+'fe/main.php?page=post_insert')

	# b.driver.implicitly_wait(1)
	# accept_button = b.select_element('div.modal-footer > button')
	# accept_button.click()
	# post_button = b.select_element('[data-href="/fe/main.php?page=post_insert"]')
	# post_button.click()
	accept2_button = b.select_element('[id="accetto"]')
	accept2_button.click()
	b.select_dropdown('[id = "categoria-ins"]',"31")
	ps_data = account_data['data'].split(":")
	email = ps_data[0]
	ages = [21,22,23,24,25,26,27,28,29,30]
	age = random.choice(ages)

	b_sub = b.select_element('[id="titolo-ins"]')
	b_sub.send_keys(postinfo['subject'])
	b_body = b.select_element('[id="testo-ins"]')
	b_body.send_keys(postinfo['body'])
	b_age = b.select_element('[id="eta-ins"]')
	b_age.send_keys(age)
	b_email = b.select_element('[name="email"]')
	b_email.send_keys(email)

	b_checkbox1 = b.select_element_xpath('//input[@id="privacy-ins"]')


	b.scroll_element_into_view(b_checkbox1)
	# b.driver.implicitly_wait(1)
	b_checkbox1.click()
	chacha_worker = capcha('73644003524468b0603694eff6fb6e6f','4191a9a8a00ad6ce300a49d8d36935da')




	site_url = b.current_url()

	chacha_key = chacha_worker.two_captcha('6LfWoxsTAAAAABGVn50YiJZfNmDDe-rD-59LAWh4', site_url)

	chacha_respons = b.driver.find_element_by_id('g-recaptcha-response')
	b.script_run("document.getElementById('g-recaptcha-response').style.display = 'block';")
	script = 'document.getElementById("g-recaptcha-response").innerHTML="{}";'.format(chacha_key)
	b.script_run(script)
	# chacha_respons.send_keys(chacha_key)
	# print(chacha_respons.get_attribute('innerHTML'))
	b.script_run("document.getElementById('g-recaptcha-response').style.display = 'none';")
	b.select_element('[id="accept-gdpr"]').click()
	# pulic_link = b.select_element('[id="pub-gratis"]')
	# b.scroll_element_into_view(pulic_link)
	# pulic_link.click()

	set_submit = b.select_element('[id="submit-ins"]')
	b.scroll_element_into_view(set_submit)
	set_submit.click()
	promo_premium = b.select_element_xpath("//*[text()='Non mostrare più questo messaggio']")
	# """"<a class="lb-close-w" href="javascript:void(0)" onclick="javascript:dontShowMsgPromoVideoChiama('bakecaincontrii.com');">Non mostrare più questo messaggio</a>"""
	# promo_premium = b.select_element('[id="promo-premium-actions"] > a')
	#//*[@id="promo-premium-actions"]/a
	# b.script_run("return dontShowMsgPromoVideoChiama('bakecaincontrii.com');")
	# b.scroll_element_into_view(promo_premium)
	promo_premium.click()
	# time.sleep(1)
	published_btn = b.select_element('[id="pub-gratis"]')
	b.scroll_element_into_view(published_btn)
	published_btn.click()


	popmail = imap('bonacatagreco100@gmail.com', "mdmdmdmd123", 'imap.gmail.com')

	counter=0
	postdone = False

	while True:
		if postdone == True:
			break
			postdone = False

		counter = counter+1
		popmail.messages(email)
		links = popmail.get_link()
		for link in links:

			conf_link = 'window.location.href = "{};'.format(link)
			print(conf_link)
			b.script_run(conf_link)
			postlink = b.select_element('#colonna-unica > div.ins-messaggio.pub > p:nth-child(2) > a')
			b.link_save(postlink.get_attribute('href'))
			postdone = True



		if counter > 10:
			worker_acc.account_ban(account_id)
			time.sleep(6)
			print("link not recived")
			break
	print('browser close')

	b.exit()
	account_id = 'profiles/' + account_id
	shutil.rmtree(account_id)


	print(datetime.now().strftime("%H:%M:%S"))






setup = table()
setup.license_verify()
#w = int(input('how much worker you need? '))
# worker = w + 1
worker = 2
# ........................start worker....................
open('active.txt', "w+")
utility = helper()
threads = []
headers = {}
profile_ids = {}
pid = threading.local()
urls = [	'https://agrigento.bakecaincontrii.com/',
			'https://ancona.bakecaincontrii.com/',
			'https://arezzo.bakecaincontrii.com/',
			'https://asti.bakecaincontrii.com/',
			'https://bari.bakecaincontrii.com/',
			'https://belluno.bakecaincontrii.com/',
			'https://bergamo.bakecaincontrii.com/',
			'https://bologna.bakecaincontrii.com/',
			'https://brescia.bakecaincontrii.com/',
			'https://cagliari.bakecaincontrii.com/',
			'https://campobasso.bakecaincontrii.com/',
			'https://caserta.bakecaincontrii.com/',
			'https://catanzaro.bakecaincontrii.com/',
			'https://cremona.bakecaincontrii.com/',
			'https://cremona.bakecaincontrii.com/',
			'https://cuneo.bakecaincontrii.com/',
			'https://fermo.bakecaincontrii.com/',
			'https://firenze.bakecaincontrii.com/',
			'https://forli.bakecaincontrii.com/',
			'https://genova.bakecaincontrii.com/',
			'https://grosseto.bakecaincontrii.com/',
			'https://isernia.bakecaincontrii.com/',
			'https://laspezia.bakecaincontrii.com/',
			'https://lecce.bakecaincontrii.com/',
			'https://livorno.bakecaincontrii.com/',
			'https://lucca.bakecaincontrii.com/',
			'https://mantova.bakecaincontrii.com/',
			'https://matera.bakecaincontrii.com/',
			'https://messina.bakecaincontrii.com/',
			'https://modena.bakecaincontrii.com/',
			'https://napoli.bakecaincontrii.com/',
			'https://nuoro.bakecaincontrii.com/',
			'https://olbiatempio.bakecaincontrii.com/',
			'https://padova.bakecaincontrii.com/',
			'https://parma.bakecaincontrii.com/',
			'https://perugia.bakecaincontrii.com/',
			'https://piacenza.bakecaincontrii.com/',
			'https://pistoia.bakecaincontrii.com/',
			'https://potenza.bakecaincontrii.com/',
			'https://ragusa.bakecaincontrii.com/',
			'https://reggiocalabria.bakecaincontrii.com/',
			'https://rieti.bakecaincontrii.com/',
			'https://roma.bakecaincontrii.com/',
			'https://salerno.bakecaincontrii.com/',
			'https://savona.bakecaincontrii.com/',
			'https://siracusa.bakecaincontrii.com/',
			'https://taranto.bakecaincontrii.com/',
			'https://terni.bakecaincontrii.com/',
			'https://trapani.bakecaincontrii.com/',
			'https://treviso.bakecaincontrii.com/',
			'https://varese.bakecaincontrii.com/',
			'https://verbania.bakecaincontrii.com/',
			'https://verona.bakecaincontrii.com/',
			'https://vicenza.bakecaincontrii.com/',
			'https://viterbo.bakecaincontrii.com/',
			'https://vibovalentia.bakecaincontrii.com/',
			'https://vercelli.bakecaincontrii.com/',
			'https://venezia.bakecaincontrii.com/',
			'https://urbino.bakecaincontrii.com/',
			'https://udine.bakecaincontrii.com/',
			'https://trieste.bakecaincontrii.com/',
			'https://trento.bakecaincontrii.com/',
			'https://torino.bakecaincontrii.com/',
			'https://teramo.bakecaincontrii.com/',
			'https://sondrio.bakecaincontrii.com/',
			'https://siena.bakecaincontrii.com/',
			'https://sassari.bakecaincontrii.com/',
			'https://rovigo.bakecaincontrii.com/',
			'https://rimini.bakecaincontrii.com/',
			'https://reggioemilia.bakecaincontrii.com/',
			'https://ravenna.bakecaincontrii.com/',
			'https://prato.bakecaincontrii.com/',
			'https://pordenone.bakecaincontrii.com/',
			'https://pisa.bakecaincontrii.com/',
			'https://pescara.bakecaincontrii.com/',
			'https://pavia.bakecaincontrii.com/',
			'https://palermo.bakecaincontrii.com/',
			'https://oristano.bakecaincontrii.com/',
			'https://ogliastra.bakecaincontrii.com/',
			'https://novara.bakecaincontrii.com/',
			'https://monza.bakecaincontrii.com/',
			'https://milano.bakecaincontrii.com/',
			'https://mediocampidano.bakecaincontrii.com/',
			'https://massacarrara.bakecaincontrii.com/',
			'https://macerata.bakecaincontrii.com/',
			'https://lodi.bakecaincontrii.com/',
			'https://lecco.bakecaincontrii.com/',
			'https://latina.bakecaincontrii.com/',
			'https://laquila.bakecaincontrii.com/',
			'https://imperia.bakecaincontrii.com/',
			'https://gorizia.bakecaincontrii.com/',
			'https://frosinone.bakecaincontrii.com/',
			'https://foggia.bakecaincontrii.com/',
			'https://ferrara.bakecaincontrii.com/',
			'https://enna.bakecaincontrii.com/',
			'https://crotone.bakecaincontrii.com/',
			'https://cosenza.bakecaincontrii.com/',
			'https://chieti.bakecaincontrii.com/',
			'https://catania.bakecaincontrii.com/',
			'https://carboniaiglesias.bakecaincontrii.com/',
			'https://caltanissetta.bakecaincontrii.com/',
			'https://brindisi.bakecaincontrii.com/',
			'https://bolzano.bakecaincontrii.com/',
			'https://biella.bakecaincontrii.com/',
			'https://benevento.bakecaincontrii.com/',
			'https://barletta.bakecaincontrii.com/',
			'https://avellino.bakecaincontrii.com/',
			'https://ascoli.bakecaincontrii.com/',
			'https://aosta.bakecaincontrii.com/',
			'https://alessandria.bakecaincontrii.com/'
		]

acc = accounts()
post = post()
co=0
while True:
	if co >3:
		co=0
		# mouse.position = (x, y)
		# mouse.move(1, 1)
		# # Press and release
		# mouse.press(Button.left)
		# mouse.release(Button.left)
		# mouse.press(Button.left)
		# mouse.release(Button.left)

	acc.save()
	post.save()


	if worker > threading.active_count():




		url = random.choice(urls)
		one_account = acc.get_account()
		postinfo = post.get_post()
		if one_account == None or postinfo == None:
			print('post or account not find for worker')
			time.sleep(10)
			continue

		if path.isdir('profiles/' +str(one_account['id'])) == True:
			shutil.rmtree('profiles/' +str(one_account['id']))

		t = threading.Thread(target=main, args=(one_account,url,postinfo,))
		acc.account_inactive(one_account['id'])

		threads.append(t)
		t.setName(one_account['id'])
		t.start()
		time.sleep(50)

		co = co+1

	else:

		# print('..............active thread :' + str(threading.active_count()) + '...............')
		time.sleep(2)
