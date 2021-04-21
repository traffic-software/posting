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
# from pynput.mouse import Button, Controller

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

def resource_path(relative_path):
	""" Get absolute path to resource, works for dev and for PyInstaller """
	base_path = getattr(sys, '_MEIPASS', path.dirname(path.abspath(__file__)))
	return path.join(base_path, relative_path)
def main(account_data,url,postinfo,packages_id):
	#show work start time
	print(datetime.now().strftime("%H:%M:%S"))
	# thread name
	account_id = threading.currentThread().getName()


	worker = psThread(account_id)
	b = browser(account_id,packages_id)
	time.sleep(10)
	worker_acc=accounts()
	
	b.get_url(url)
	try:
		b.script_run('return  accept_privacy_cookie()')
		
	except:
		print('accept_privacy_cookie error')
	
	try:
		b.script_run('return  siaccetto18()')
	except:
		print('siaccetto18 error')

	
	accept1_button = b.select_element_xpath('//*[@id="lightbox-vm18"]/div/div/div[3]/button')
	accept1_button.click()
	
	accept2_button = b.select_element_xpath('//*[@id="app"]/div[3]/button[2]')
	accept2_button.click()
	

	
	try:
		# city = random.choice(citys)
		b.select_dropdown_by_text('[name="category"]',"Kinesiologas")
		#5c8a2993c5591de8c6236nod4e
	except:
		print('category error')
	try:
		citys = ["Ayacucho","Cajamarca","Callao","Chiclayo","Chimbote","Cusco","Huacho","Huancayo","Huánuco","Huaraz","Ica","Iquitos","Juliaca","Lambayeque","Lima Metropolitana","Piura","Pucallpa","Puno","Tacna","Tarapoto","Trujillo"]
		city = random.choice(citys)
		b.select_dropdown_by_text('[name="city"]',city)
	except:
		print('city error')
	
	ps_data = account_data['data'].split(":")
	email = ps_data[0]
	popmail = imap(ps_data[0], ps_data[1], ps_data[2])
	popmail.messages(email)
	popmail.close()
	ages = [21,22,23,24,25,26,27,28,29,30]
	age = random.choice(ages)
	b_sub = b.select_element('[name="title"]')
	b_sub.send_keys(postinfo['subject'])
	b.scroll_element_into_view(b_sub)
	b_body = b.select_element_xpath('//*[@id="app"]/main/div/form/div/div[2]/div/div[7]/textarea')
	b.scroll_element_into_view(b_body)
	b_body.send_keys(postinfo['body'])
	b_age = b.select_element('[name="age"]')
	b_age.send_keys(age)
	b_email = b.select_element('[name="email"]')
	b_email.send_keys(email)
	
	# .prop("checked", true) or .click() or .trigger("click")
	b.script_run('return  $("#contact_method_only_email").trigger("click")')
	checkbox2 = '''return  $('input[name="terms"]').click()'''
	b.script_run(checkbox2)
	# b.captcha()
	chacha_worker = capcha('73644003524468b0603694eff6fb6e6f','4191a9a8a00ad6ce300a49d8d36935da')




	site_url = b.current_url()

	chacha_key = chacha_worker.two_captcha('6LfWoxsTAAAAABGVn50YiJZfNmDDe-rD-59LAWh4', site_url)

	chacha_respons = b.driver.find_element_by_id('g-recaptcha-response')
	print('g-recaptcha-response')
	b.script_run("document.getElementById('g-recaptcha-response').style.display = 'block';")
	print('g-recaptcha-response block')
	script = 'document.getElementById("g-recaptcha-response").innerHTML="{}";'.format(chacha_key)
	
	b.script_run(script)
	print('g-recaptcha-response set data')
	b.script_run("document.getElementById('g-recaptcha-response').style.display = 'none';")
	print('g-recaptcha-response none')



	# submit1 =b.select_element('[id="accept-gdpr"]')
	# submit1.click()
	try:
		b.script_run("return  dontShowMsgPromoVideoChiama('bakecaincontrii.com')")
	except:
		print('dontShowMsgPromoVideoChiama error')
	

	set_submit = b.select_element_xpath('//*[@id="app"]/main/div/form/div/div[10]/div/button')
	b.scroll_element_into_view(set_submit)
	set_submit.click()
	
	# published_btn = b.select_element('[id="pub-gratis"]')
	# b.scroll_element_into_view(published_btn)
	# published_btn.click()


	popmail = imap(ps_data[0], ps_data[1], ps_data[2])
	

	counter=0
	postdone = False

	while True:
		time.sleep(10)
		if postdone == True:
			break
			postdone = False

		counter = counter+1
		
		popmail.messages(email)
		links = popmail.get_link()
		
		print('links')
		print(links)
		
		for link in links:

			conf_link = 'window.location.href = "{};'.format(link)
			b.script_run(conf_link)
			postlink = b.select_element('#colonna-unica > div.ins-messaggio.pub > p:nth-child(2) > a')
			b.link_save(postlink.get_attribute('href'))
			worker_acc.post_done(account_id)
			worker_acc.account_active(account_id)
			postdone = True


		
		if counter > 6:
			worker_acc.ban(account_id)
			
			print("link not recived")
			break
	print('browser close')

	

	b.exit()
	popmail.close()
	


	print(datetime.now().strftime("%H:%M:%S"))






setup = table()
setup.license_verify()
#w = int(input('how much worker you need? '))
# packages_id = input('proxy info by a line : ')
packages_id = 'no'
# worker = w + 1
worker = 2
# ........................start worker....................
open('active.txt', "w+")
utility = helper()
threads = []
headers = {}
profile_ids = {}
pid = threading.local()
urls = ['https://pe.skokka.com/u/post-insert/']

acc = accounts()
post = post()
co=0
while True:
	utility.network_check()
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

	acc.account_Reactive()
	post.save()



	if worker > threading.active_count():




		url = random.choice(urls)

		one_account = acc.get_account()
		
		postinfo = post.get_post()
		if one_account == None or postinfo == None:
			print('post or account not find for worker')
			time.sleep(60)
			continue
		print('account last use time is : ',one_account['used_at'])
		

		if path.isdir('profiles/' +str(one_account['id'])) == True:
			shutil.rmtree('profiles/' +str(one_account['id']))

		t = threading.Thread(target=main, args=(one_account,url,postinfo,packages_id,))
		acc.account_inactive(one_account['id'])
		acc.post_done(one_account['id'])

		threads.append(t)
		t.setName(one_account['id'])
		t.start()
		

		co = co+1

	else:

		# print('..............active thread :' + str(threading.active_count()) + '...............')
		time.sleep(2)
