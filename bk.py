from email.policy import SMTP
import threading
import time
import shutil
import random
import string
import fnmatch
import sys
from os import path
from pyvirtualdisplay import Display
from datetime import datetime
import smtp
from ps_lib.browser import browser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.ps_str import ps_str
from ps_lib.imap import imap
from selenium.webdriver.common.keys import Keys
import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))
# from pynput.mouse import Button, Controller





def main(account_data,postinfo,packages_id,body_mail):
	#work start time
	starttime=datetime.now().strftime("%H:%M:%S")

	print(datetime.now().strftime("%H:%M:%S"))
	
	account_id = account_data['id']
	print('accountd id : ',account_id)
	worker_acc=accounts()
	settings = table()
	popacc = settings.pop_verify()
	pp = "pva_pop" == popacc
	if not pp:
		pop = popacc.split(":")
		popmail = imap(account_id,pop[0],pop[1])
	else:
		popmail = imap(account_id,account_data['email'],account_data['password'])
	
	popmail.messages('no_reply@bakecaincontrii.com')
	popmail.close()


	profile_dir="{}/profiles/{}".format(bundle_dir,account_id)
	p_pass= "4mdloQgXxS8lcB3J_country-Italy_session-%s"% (''.join(random.choice(string.ascii_letters) for i in range(10)))
	b = browser(account_id,packages_id,proxy_company='packetstream',proxy_country="Italy",proxy_user='malaknoyn',proxy_pass=p_pass,use_proxy=False,profile_dir=profile_dir)
	time.sleep(5)
	urls = ['brescia','cagliari','campobasso','caserta','catanzaro','cremona','cremona','cuneo','fermo','firenze','forli','genova','grosseto','isernia','laspezia','lecce','livorno','lucca','mantova','matera','messina','modena','napoli','nuoro','olbiatempio','padova','parma','perugia','piacenza','pistoia','potenza','ragusa','reggiocalabria','rieti','roma','salerno','savona','siracusa','taranto','terni','trapani','treviso','varese','verbania','verona','vicenza','viterbo','vibovalentia','vercelli','venezia','urbino','udine','trieste','trento','torino','teramo','sondrio','siena','sassari','rovigo','rimini','reggioemilia','ravenna','prato','pordenone','pisa','pescara','pavia','palermo','oristano','ogliastra','novara','monza','milano','mediocampidano','massacarrara','macerata','lodi','lecco','latina','laquila','imperia','gorizia','frosinone','foggia','ferrara','enna','crotone','cosenza','chieti','catania','carboniaiglesias','caltanissetta','brindisi','bolzano','biella','benevento','barletta','avellino','ascoli','aosta','alessandria']
	url = random.choice(urls)
	if b.proxy_city is not None:
		pattern = '*%s*'%(b.proxy_city)
		citys = fnmatch.filter(urls, pattern)
		if len(citys)>0:
			url = citys[0]
	
	
		
	try:
		b.get_url('https://'+url+'.bakecaincontrii.com/fe/main.php?page=post_insert')
	except:
		b.exit()
	
	accept1_button = b.select_element_xpath('//*[@id="lightbox-vm18"]/div/div/div[3]/button','accept1_button')
	accept1_button.click()
	accept2_button = b.select_element_xpath('//*[@id="app"]/div[3]/button[2]','accept2_button')
	accept2_button.click()

	
	try:
		citylist =["Agrigento","Alessandria","Ancona","Aosta","Arezzo","Ascoli","Asti","Avellino","Bari","Barletta","Belluno","Benevento","Bergamo","Biella","Bologna","Bolzano","Brescia","Brindisi","Cagliari","Caltanissetta","Campobasso","Carbonia Iglesias","Caserta","Catania","Catanzaro","Chieti","Como","Cosenza","Cremona","Crotone","Cuneo","Enna","Fermo","Ferrara","Firenze","L'Aquila","La Spezia","Latina","Lecce","Lecco","Livorno","Lodi","Lucca","Macerata","Mantova","Massa Carrara","Matera","Medio Campidano","Messina","Milano"," Modena","Monza","Napoli","Novara","Nuoro"," Ogliastra","Olbia Tempio","Oristano","Padova","Palermo","Parma","Pavia","Perugia","Pescara","Piacenza","Pisa","Pistoia","Pordenone","Potenza","Prato"," Ragusa","Ravenna","Reggio Calabria","R. Emilia","Rieti","Rimini","Roma","Rovigo","Salerno","Sassari","Savona","Siena","Siracusa","Sondrio","Taranto","Teramo","Terni"," Torino","Trapani","Trento","Treviso","Trieste","Udine","Urbino","Varese","Venezia","Verbania","Vercelli","Verona","Vibo Valentia","Vicenza","Viterbo"]
		one_city = random.choice(citylist)
		if b.proxy_city is not None:
			pattern = '*%s*'%(b.proxy_city)
			citylist = fnmatch.filter(citylist, pattern)
			if len(citylist)>0:
				one_city = citylist[0]
			
		b.select_dropdown_text('city',one_city)
	except:
		print('city error')
	try:
		# category= b.select_element_xpath('//*[@id="app"]/main/div[2]/form/div/div[2]/div/div[1]/select/option[1]')
		b.select_dropdown_text('category','Donna Cerca Uomo')
		
		# category.click()
	except:
		print('category error')
	
	
	ages = [18,19,20,21,22,23,24,25,26,27,28,29,30]
	age = random.choice(ages)

	b_sub = b.select_element_xpath('//*[@id="app"]/main/div[2]/form/div/div[3]/div/div[2]/textarea','select subject')
	postsub = ps_str(postinfo['data1'])
	b_sub.send_keys(postsub.Spin())
	b_body = b.select_element_xpath('//*[@id="app"]/main/div[2]/form/div/div[3]/div/div[3]/textarea','select body')
	postbody = ps_str(postinfo['data4'])
	b_body.send_keys(postbody.with_email(body_mail))
	b_age = b.select_element_xpath('//*[@id="app"]/main/div[2]/form/div/div[3]/div/div[1]/input','select age')
	b_age.send_keys(age)
	b_email = b.select_element_xpath('//*[@id="email_input"]','select email')
	b_email.send_keys(account_data['email'])
	
	b.script_run('return  $("#contact_method_only_email").trigger("click")','click contact method')
	checkbox2 = '''return  $('input[name="terms"]').prop("checked", true)'''
	b.script_run(checkbox2,'accept terms')
	btn_remove = '''$("button.btn.btn-primary.waves-effect.btn-block").remove();'''
	b.script_run(btn_remove,"form sbumit button remove")

	


	# captcha done by auto

	# site_url = b.current_url()

	
	# try:

	# 	captcha = b.driver.find_element_by_name('h-captcha-response')
	# except Exception as e:
	# 	worker_acc.post_error(account_id,'captcha not load')
	# 	print('captcha not load')
	# 	b.exit()
	# 	exit()
	# b.script_run("document.getElementById('{0}').style.display = 'block';".format(captcha.get_attribute('id')),message='captcha display block')
		
	# chacha_worker = capcha('73644003524468b0603694eff6fb6e6f','4191a9a8a00ad6ce300a49d8d36935da',1,lan='it')
	# c_info = chacha_worker.two_captcha('a5c093a2-bc6f-4e21-a32b-003180834ca6', site_url)
	# script = 'document.getElementById("{0}").innerHTML="{1}";'.format(captcha.get_attribute('id'),c_info["key"])
		
	# b.script_run(script,message='captcha key add')
	# b.script_run("document.getElementById('{0}').style.display = 'none';".format(captcha.get_attribute('id')),message='captcha done')
	
	
	# captcha done by menual
	print('Please complete the captcha \n i\'m waiting for captcha')
	sec = input('Press the enter button')
		

	

	
	btn_click = '''$("form").submit()'''
	b.script_run(btn_click,"form sbumit")
	
	img = b.select_element_xpath('//*[@id="app"]/main/form/div/div[4]/div/button','image upload')
	b.scroll_element_into_view(img)
	img.click()
	Visibility = b.select_element_xpath('//*[@id="app"]/main/form/div[2]/div[2]/div[2]/div/div/div/button','Visibility')
	b.scroll_element_into_view(Visibility)
	Visibility.click()

	if not pp:
		popmail = imap(account_id,pop[0],pop[1])
	else:
		popmail = imap(account_id,account_data['email'],account_data['password'])
	

	counter=0
	postdone = False
	
	while True:
		
		if postdone == True:
			break
			postdone = False
		time.sleep(10)

		counter = counter+1
		
		popmail.messages('no_reply@bakecaincontrii.com')
		links = popmail.get_link('post-publish')
		
		print('links')
		
		for link in links:

			conf_link = 'window.location.href = "{};'.format(link)
			b.script_run(conf_link,'link click to verify')
			
			worker_acc.post_done(account_id,link)
			
			postdone = True
			break


		
		if counter > 6:
			worker_acc.post_error(account_id,'verify link not recived')
			worker_acc.ban_3(account_id,status=2)
			print("link not recived")
			break
		
	print('browser close')

	

	b.exit()
	popmail.close()
	


	print('start :',starttime)
	print('end :',datetime.now().strftime("%H:%M:%S"))






setup = table()
setup.token_verify()

#w = int(input('how much worker you need? '))
# packages_id = input('proxy info by a line : ')
packages_id = '317345'

# worker = w + 1
worker = 2
# ........................start worker....................
open('active.txt', "w+")
utility = helper()
headers = {}
profile_ids = {}
acc = accounts()
post = post()
if sys.platform not in ['Windows', 'win32', 'cygwin']:
	display = Display(visible=0, size=(1024, 768))
	display.start()
# x = threading.Thread(target=smtp.reply_check, args=(1,), daemon=True)
# x.start()
while True:
	utility.network_check()
	if setup.token_off():
		print('software off now but reply checking runing')
		time.sleep(60)
		continue
	one_account = acc.get_account()
		
	postinfo = post.get_post()
	body_mail=post.get_body_mail()
	if one_account == None or postinfo == None:
		print('post or account not find for worker')
		time.sleep(60)
		continue
	print('account last use time is : ',one_account['last_updates'])
		

	if path.isdir('profiles/' +str(one_account['id'])) == True:
		# shutil.rmtree('profiles/' +str(one_account['id']))
		pass
		
	print('main')
	main(one_account,postinfo,packages_id,body_mail)
	time.sleep(10)

		

	