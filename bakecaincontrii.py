import threading
from selenium.webdriver.common.keys import Keys
import time
import shutil
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
# b = browser('545')
#
# b.get_url('http://httpbin.org/get')
# exit()


def main(account_data,url,postinfo):
	#show work start time
	print(datetime.now().strftime("%H:%M:%S"))
	# thread name
	account_id = threading.currentThread().getName()

	print(str(account_id) + "\t" + str(account_data))

	worker = psThread(account_id)
	b = browser(account_id)

	b.get_url(url)
	time.sleep(2)
	accept_button = b.select_element('div.modal-footer > button')
	accept_button.click()
	post_button = b.select_element('[data-href="/fe/main.php?page=post_insert"]')
	post_button.click()
	accept2_button = b.select_element('[name="subprocedi18"]')
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
	time.sleep(1)
	b_checkbox1.click()
	chacha_worker = capcha('73644003524468b0603694eff6fb6e6f')




	site_url = b.current_url()

	chacha_key = chacha_worker.anticaptcha('6LfWoxsTAAAAABGVn50YiJZfNmDDe-rD-59LAWh4', site_url)
	print(chacha_key)
	chacha_respons = b.driver.find_element_by_id('g-recaptcha-response')
	b.script_run("document.getElementById('g-recaptcha-response').style.display = 'block';")
	script = 'document.getElementById("g-recaptcha-response").innerHTML="{}";'.format(chacha_key)
	b.script_run(script)
	print(chacha_respons)
	# chacha_respons.send_keys(chacha_key)
	print(chacha_respons.get_attribute('innerHTML'))
	b.script_run("document.getElementById('g-recaptcha-response').style.display = 'none';")
	b.select_element('[id="accept-gdpr"]').click()
	# pulic_link = b.select_element('[id="pub-gratis"]')
	# b.scroll_element_into_view(pulic_link)
	# pulic_link.click()

	set_submit = b.select_element('[id="submit-ins"]')
	b.scroll_element_into_view(set_submit)
	time.sleep(1)
	set_submit.click()
	time.sleep(1)
	promo_premium = b.select_element('[id="promo-premium-actions"] > a')
	b.scroll_element_into_view(promo_premium)
	promo_premium.click()
	time.sleep(1)
	published_btn = b.select_element('[id="pub-gratis"]')
	b.scroll_element_into_view(published_btn)
	published_btn.click()




	time.sleep(1)


	popmail = imap('michaelnguyen1144@gmail.com', "jqjokiwa@@# ", 'imap.gmail.com')

	counter=0

	while True:
		counter = counter+1
		popmail.messages(email)
		links = popmail.get_link()
		for link in links:

			conf_link = 'window.location.href = "{};'.format(link)
			print(conf_link)
			b.script_run(conf_link)
			time.sleep(30)


		if counter > 5:
			time.sleep(100)
			exit("link not recived")
			#7fdb52b52b4ceceebfbde0833d7cc8a1
			break

	print('browser close')
	time.sleep(9)
	b.exit()
	account_id = 'profiles/'+account_id
	shutil.rmtree(account_id)

	print(datetime.now().strftime("%H:%M:%S"))






setup = table()
#w = int(input('how much worker you need? '))
# worker = w + 1
worker = 2
# ........................start worker....................
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
urls = [	'https://agrigento.bakecaincontrii.com/donna-cerca-uomo',
			'https://ancona.bakecaincontrii.com/donna-cerca-uomo',
			'https://arezzo.bakecaincontrii.com/donna-cerca-uomo',
			'https://asti.bakecaincontrii.com/donna-cerca-uomo',
			'https://bari.bakecaincontrii.com/donna-cerca-uomo',
			'https://belluno.bakecaincontrii.com/donna-cerca-uomo',
			'https://bergamo.bakecaincontrii.com/donna-cerca-uomo',
			'https://bologna.bakecaincontrii.com/donna-cerca-uomo',
			'https://brescia.bakecaincontrii.com/donna-cerca-uomo',
			'https://cagliari.bakecaincontrii.com/donna-cerca-uomo',
			'https://campobasso.bakecaincontrii.com/donna-cerca-uomo',
			'https://caserta.bakecaincontrii.com/donna-cerca-uomo',
			'https://catanzaro.bakecaincontrii.com/donna-cerca-uomo',
			'https://cremona.bakecaincontrii.com/donna-cerca-uomo',
			'https://cremona.bakecaincontrii.com/donna-cerca-uomo',
			'https://cuneo.bakecaincontrii.com/donna-cerca-uomo',
			'https://fermo.bakecaincontrii.com/donna-cerca-uomo',
			'https://firenze.bakecaincontrii.com/donna-cerca-uomo',
			'https://forli.bakecaincontrii.com/donna-cerca-uomo',
			'https://genova.bakecaincontrii.com/donna-cerca-uomo',
			'https://grosseto.bakecaincontrii.com/donna-cerca-uomo',
			'https://isernia.bakecaincontrii.com/donna-cerca-uomo',
			'https://laspezia.bakecaincontrii.com/donna-cerca-uomo',
			'https://lecce.bakecaincontrii.com/donna-cerca-uomo',
			'https://livorno.bakecaincontrii.com/donna-cerca-uomo',
			'https://lucca.bakecaincontrii.com/donna-cerca-uomo',
			'https://mantova.bakecaincontrii.com/donna-cerca-uomo',
			'https://matera.bakecaincontrii.com/donna-cerca-uomo',
			'https://messina.bakecaincontrii.com/donna-cerca-uomo',
			'https://modena.bakecaincontrii.com/donna-cerca-uomo',
			'https://napoli.bakecaincontrii.com/donna-cerca-uomo',
			'https://nuoro.bakecaincontrii.com/donna-cerca-uomo',
			'https://olbiatempio.bakecaincontrii.com/donna-cerca-uomo',
			'https://padova.bakecaincontrii.com/donna-cerca-uomo',
			'https://parma.bakecaincontrii.com/donna-cerca-uomo',
			'https://perugia.bakecaincontrii.com/donna-cerca-uomo',
			'https://piacenza.bakecaincontrii.com/donna-cerca-uomo',
			'https://pistoia.bakecaincontrii.com/donna-cerca-uomo',
			'https://potenza.bakecaincontrii.com/donna-cerca-uomo',
			'https://ragusa.bakecaincontrii.com/donna-cerca-uomo',
			'https://reggiocalabria.bakecaincontrii.com/donna-cerca-uomo',
			'https://rieti.bakecaincontrii.com/donna-cerca-uomo',
			'https://roma.bakecaincontrii.com/donna-cerca-uomo',
			'https://salerno.bakecaincontrii.com/donna-cerca-uomo',
			'https://savona.bakecaincontrii.com/donna-cerca-uomo',
			'https://siracusa.bakecaincontrii.com/donna-cerca-uomo',
			'https://taranto.bakecaincontrii.com/donna-cerca-uomo',
			'https://terni.bakecaincontrii.com/donna-cerca-uomo',
			'https://trapani.bakecaincontrii.com/donna-cerca-uomo',
			'https://treviso.bakecaincontrii.com/donna-cerca-uomo',
			'https://varese.bakecaincontrii.com/donna-cerca-uomo',
			'https://verbania.bakecaincontrii.com/donna-cerca-uomo',
			'https://verona.bakecaincontrii.com/donna-cerca-uomo',
			'https://vicenza.bakecaincontrii.com/donna-cerca-uomo',
			'https://viterbo.bakecaincontrii.com/donna-cerca-uomo',
			'https://vibovalentia.bakecaincontrii.com/donna-cerca-uomo',
			'https://vercelli.bakecaincontrii.com/donna-cerca-uomo',
			'https://venezia.bakecaincontrii.com/donna-cerca-uomo',
			'https://urbino.bakecaincontrii.com/donna-cerca-uomo',
			'https://udine.bakecaincontrii.com/donna-cerca-uomo',
			'https://trieste.bakecaincontrii.com/donna-cerca-uomo',
			'https://trento.bakecaincontrii.com/donna-cerca-uomo',
			'https://torino.bakecaincontrii.com/donna-cerca-uomo',
			'https://teramo.bakecaincontrii.com/donna-cerca-uomo',
			'https://sondrio.bakecaincontrii.com/donna-cerca-uomo',
			'https://siena.bakecaincontrii.com/donna-cerca-uomo',
			'https://sassari.bakecaincontrii.com/donna-cerca-uomo',
			'https://rovigo.bakecaincontrii.com/donna-cerca-uomo',
			'https://rimini.bakecaincontrii.com/donna-cerca-uomo',
			'https://reggioemilia.bakecaincontrii.com/donna-cerca-uomo',
			'https://ravenna.bakecaincontrii.com/donna-cerca-uomo',
			'https://prato.bakecaincontrii.com/donna-cerca-uomo',
			'https://pordenone.bakecaincontrii.com/donna-cerca-uomo',
			'https://pisa.bakecaincontrii.com/donna-cerca-uomo',
			'https://pescara.bakecaincontrii.com/donna-cerca-uomo',
			'https://pavia.bakecaincontrii.com/donna-cerca-uomo',
			'https://palermo.bakecaincontrii.com/donna-cerca-uomo',
			'https://oristano.bakecaincontrii.com/donna-cerca-uomo',
			'https://ogliastra.bakecaincontrii.com/donna-cerca-uomo',
			'https://novara.bakecaincontrii.com/donna-cerca-uomo',
			'https://monza.bakecaincontrii.com/donna-cerca-uomo',
			'https://milano.bakecaincontrii.com/donna-cerca-uomo',
			'https://mediocampidano.bakecaincontrii.com/donna-cerca-uomo',
			'https://massacarrara.bakecaincontrii.com/donna-cerca-uomo',
			'https://macerata.bakecaincontrii.com/donna-cerca-uomo',
			'https://lodi.bakecaincontrii.com/donna-cerca-uomo',
			'https://lecco.bakecaincontrii.com/donna-cerca-uomo',
			'https://latina.bakecaincontrii.com/donna-cerca-uomo',
			'https://laquila.bakecaincontrii.com/donna-cerca-uomo',
			'https://imperia.bakecaincontrii.com/donna-cerca-uomo',
			'https://gorizia.bakecaincontrii.com/donna-cerca-uomo',
			'https://frosinone.bakecaincontrii.com/donna-cerca-uomo',
			'https://foggia.bakecaincontrii.com/donna-cerca-uomo',
			'https://ferrara.bakecaincontrii.com/donna-cerca-uomo',
			'https://enna.bakecaincontrii.com/donna-cerca-uomo',
			'https://crotone.bakecaincontrii.com/donna-cerca-uomo',
			'https://cosenza.bakecaincontrii.com/donna-cerca-uomo',
			'https://chieti.bakecaincontrii.com/donna-cerca-uomo',
			'https://catania.bakecaincontrii.com/donna-cerca-uomo',
			'https://carboniaiglesias.bakecaincontrii.com/donna-cerca-uomo',
			'https://caltanissetta.bakecaincontrii.com/donna-cerca-uomo',
			'https://brindisi.bakecaincontrii.com/donna-cerca-uomo',
			'https://bolzano.bakecaincontrii.com/donna-cerca-uomo',
			'https://biella.bakecaincontrii.com/donna-cerca-uomo',
			'https://benevento.bakecaincontrii.com/donna-cerca-uomo',
			'https://barletta.bakecaincontrii.com/donna-cerca-uomo',
			'https://avellino.bakecaincontrii.com/donna-cerca-uomo',
			'https://ascoli.bakecaincontrii.com/donna-cerca-uomo',
			'https://aosta.bakecaincontrii.com/donna-cerca-uomo',
			'https://alessandria.bakecaincontrii.com/donna-cerca-uomo'
		]

acc = accounts()
post = post()
while True:
	acc.save()
	post.save()


	if worker > threading.active_count():




		url = random.choice(urls)
		one_account = acc.get_account()
		print(one_account)
		postinfo = post.get_post()
		if one_account == None and postinfo== None:
			time.sleep(10)
			acc.get_account_for_inactive()

			continue
		acc.account_active(one_account['id'])

		t = threading.Thread(target=main, args=(one_account,url,postinfo,))
		acc.account_active(one_account['id'])

		threads.append(t)
		t.setName(one_account['id'])
		t.start()
		time.sleep(50)

	else:

		print('..............active thread :' + str(threading.active_count()) + '...............')
		time.sleep(50)
