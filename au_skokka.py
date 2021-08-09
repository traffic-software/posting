import threading
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
import time
import shutil
import fnmatch
from os import path
from datetime import datetime
from ps_lib.browser import browser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.ps_str import ps_str
from ps_lib.imap import imap
import random
import string
import sys

# b = browser('545')
#
# b.get_url('http://httpbin.org/get')
# exit() 

def resource_path(relative_path):
	""" Get absolute path to resource, works for dev and for PyInstaller """
	base_path = getattr(sys, '_MEIPASS', path.dirname(path.abspath(__file__)))
	return path.join(base_path, relative_path)
def main(account_data,url,postinfo,packages_id,body_mail):
	#show work start time
	starttime=datetime.now().strftime("%H:%M:%S")
	
	account_id = account_data['id']
	p_pass= "4mdloQgXxS8lcB3J_country-Australia_session-%s"% (''.join(random.choice(string.ascii_letters) for i in range(10)))
	b = browser(account_id,packages_id,proxy_company='packetstream',proxy_country="Australia",proxy_user='malaknoyn',proxy_pass=p_pass)
	time.sleep(5)
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
	
	

	time.sleep(2)
	try:
		category= b.select_element_xpath('//*[@id="app"]/main/div[2]/form/div/div[2]/div/div[1]/select/option[2]')
		
		category.click()
		#5c8a2993c5591de8c6236nod4e
	except:
		print('category error')
	try:
		citys = ["Sydney","Melbourne","Brisbane","Perth Western Australia","Adelaide","Canberra","Gold Coast","Newcastle","Geelong"]
		city = random.choice(citys)
		if b.proxy_city is not None:
			pattern = '*%s*'%(b.proxy_city)
			citys = fnmatch.filter(citys, pattern)
			if len(citys)>0:
				city = citys[0]
			

			


			
		

		b.select_dropdown_text('city',city)
	except:
		print('city error')
	
	ps_data = account_data['data'].split(":")
	email = ps_data[0]
	popmail = imap(account_id,ps_data[0], ps_data[1], ps_data[2])
	popmail.messages(mail_from='no_reply@skokka.com')
	popmail.close()
	ages = [21,22,23,24,25,26,27,28,29,30]
	age = random.choice(ages)
	b_sub = b.select_element('[name="title"]')
	postsub = ps_str(postinfo['subject'])
	b_sub.send_keys(postsub.Spin())
	b.scroll_element_into_view(b_sub)
	
	b_body = b.select_element_xpath('//*[@id="app"]/main/div[2]/form/div/div[3]/div/div[3]/textarea')
	b.scroll_element_into_view(b_body)
	postbody = ps_str(postinfo['body'])
	b_body.send_keys(postbody.with_email(body_mail))
	b_age = b.select_element('[name="age"]')
	b_age.send_keys(age)
	b_email = b.select_element('[name="email"]')
	b_email.send_keys(email)
	
	# .prop("checked", true) or .click() or .trigger("click")
	b.script_run('return  $("#contact_method_only_email").trigger("click")')
	checkbox2 = '''return  $('input[name="terms"]').prop("checked", true)'''
	b.script_run(checkbox2)
	# b.captcha()
	chacha_worker = capcha('73644003524468b0603694eff6fb6e6f','4191a9a8a00ad6ce300a49d8d36935da',1,lan='en')




	site_url = b.current_url()

	chacha_key = chacha_worker.two_captcha('dc111e73-c47b-417a-bb11-44ae4b3734aa', site_url)
	try:

		chacha_respons = b.driver.find_element_by_name('h-captcha-response')
		print('h-captcha-response')
		b.script_run("document.getElementById('{0}').style.display = 'block';".format(chacha_respons.get_attribute('id')))
		print('h-captcha-response block')
		print(chacha_key)
		script = 'document.getElementById("{0}").innerHTML="{1}";'.format(chacha_respons.get_attribute('id'),chacha_key)
		
		b.script_run(script)
		print('h-captcha-response set data')
		b.script_run("document.getElementById('{0}').style.display = 'none';".format(chacha_respons.get_attribute('id')))
		print('h-captcha-response none')
	except Exception as e:
		print('h-captcha error',e)




	

	# set_submit = b.select_element_xpath('//*[@id="app"]/main/div/form/div/div[10]/div/button')
	# b.scroll_element_into_view(set_submit)
	# set_submit.click()
	btn_remove = '''$("button.btn.btn-primary.waves-effect.btn-block").remove();'''
	btn_add = '''$("form").append("<input type="submit" id="sub_btn" value="Continuar"/>");'''
	btn_click = '''$("form").submit()'''
	# try:
	b.script_run(btn_remove)
	# b.script_run(btn_add)
	b.script_run(btn_click)
	# except:
	
	
	img = b.select_element_xpath('//*[@id="app"]/main/form/div/div[4]/div/button')
	b.scroll_element_into_view(img)
	img.click()
	Visibility = b.select_element_xpath('//*[@id="app"]/main/form/div[2]/div[2]/div[2]/div/div/div/button')
	b.scroll_element_into_view(Visibility)
	Visibility.click()
	
	# time.sleep(60)
	# exit()


	popmail = imap(account_id,ps_data[0], ps_data[1], ps_data[2])
	

	counter=0
	postdone = False

	while True:
		time.sleep(10)
		if postdone == True:
			break
			postdone = False

		counter = counter+1
		
		popmail.messages(mail_from='no_reply@skokka.com')
		links = popmail.get_link("post-publish")
		
		print('links')
		print(links)
		
		for link in links:

			conf_link = 'window.location.href = "{};'.format(link)
			b.script_run(conf_link)
			postlink = b.select_element_xpath('//*[@id="app"]/main/div/div[4]/div/div/a')
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
	
	


	print('start :',starttime)
	print('end :',datetime.now().strftime("%H:%M:%S"))






setup = table()
setup.license_verify()
#w = int(input('how much worker you need? '))
# packages_id = input('proxy info by a line : ')
packages_id = '317345'
# worker = w + 1

# ........................start worker....................
utility = helper()
headers = {}
profile_ids = {}
urls = ['https://au.skokka.com/u/post-insert/']

acc = accounts()
post = post()
co=0
if sys.platform not in ['Windows', 'win32', 'cygwin']:
	display = Display(visible=0, size=(1024, 768))
	display.start()
while True:
	utility.network_check()

	acc.save()

	acc.account_Reactive()
	post.save()
	url = random.choice(urls)
	one_account = acc.get_account()
	postinfo = post.get_post()
	body_mail=post.get_body_mail()
	if one_account == None or postinfo == None:
		print('post or account not find for worker')
		time.sleep(60)
		continue
	print('account last use time is : ',one_account['used_at'])
		

	if path.isdir('profiles/' +str(one_account['id'])) == True:
		shutil.rmtree('profiles/' +str(one_account['id']))

	main(one_account,url,postinfo,packages_id,body_mail)
	acc.account_inactive(one_account['id'])
	acc.post_done(one_account['id'])

