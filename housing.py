from email.policy import SMTP
from re import sub
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
	print("account id: ",account_id)
	worker_acc=accounts()
	popmail = imap(account_id,account_data['email'],account_data['password'])
	popmail.messages('robot@craigslist.org')
	popmail.close()
	


	
	p_pass= "4mdloQgXxS8lcB3J_country-UnitedStates_session-%s"% (''.join(random.choice(string.ascii_letters) for i in range(9)))
	
	# p_pass= "4mdloQgXxS8lcB3J_country-UnitedStates"
	b = browser(account_id,packages_id,proxy_company='packetstream',proxy_country="UnitedStates",proxy_user='malaknoyn',proxy_pass=p_pass)
	#p_pass= "wifi;us;;;{};".format(account_data['extra'])
	# b = browser(account_id,packages_id,proxy_company='soax',proxy_country="UnitedStates",proxy_user='uyMDe7ALdLkpJmm5',proxy_pass=p_pass)
	time.sleep(5)
	
	
	
		
	try:
		b.get_url('https://craigslist.org')
	except:
		b.exit()
	
	
	button = b.select_element_xpath('//*[@id="post"]','click new post')
	button.click()
	
	
	#https://post.craigslist.org/k/sib7px0t7BGflPX08yY-RA/Qdjqi?s=subarea
	if 'subarea' in  b.current_url():
		sub_aria = b.select_elements('input[type=radio]')
		sub_aria =random.choice(sub_aria)
		
		sub_aria.click()
	if 's=hood' in  b.current_url():
		sub_aria = b.select_elements('input[type=radio]')
		sub_aria =random.choice(sub_aria)
		
		sub_aria.click()
	button = b.select_element_xpath('/html/body/article/section/form/ul/li[4]','click on housing offered')
	button.click()
	button = b.select_element_xpath('//*[@id="new-edit"]/div/label/label[2]/div/span[1]','click on apartments / housing for rent')
	button.click()

	#Posting Title setup
	b_sub = b.select_element_xpath('//*[@id="PostingTitle"]','PostingTitle')
	post=postinfo.get_post()
	postsub = ps_str(post['data1'])
	b_sub.send_keys(postsub.Spin())
	#zip code setup
	postal_code = b.select_element_xpath('//*[@id="postal_code"]','postal code"]')
	postal_code.send_keys(b.proxy_zip)

	#post body setup
	b_body = b.select_element_xpath('//*[@id="PostingBody"]','PostingBody')
	postbody = ps_str(post['data4'])
	b_body.send_keys(postbody.with_email(body_mail))

	#price setup
	b_price = b.select_element_xpath('//*[@id="new-edit"]/div/fieldset[1]/div/div[1]/label[1]/label/input','price set')
	b_price.send_keys(postinfo.price)

	#housing type setup
	try:
		type =[1,4,5,6]
		one_type= random.choice(type)
		
		append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(one_type))
		ju = str('$("#ui-id-1"){}'.format(append))
		
		b.script_run('$("#ui-id-1").empty();',message='housing_type empty')
		b.script_run(ju,message='housing_type append')
			
		
		
			
		
	except Exception as e:
		print('housing_type error' ,e)
	
	#laundry setup
	try:
		one_type=1
		append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(one_type))
		ju = str('$("#ui-id-2"){}'.format(append))
		
		b.script_run('$("#ui-id-2").empty();',message='laundry empty')
		b.script_run(ju,message='laundry append')
		# b.select_dropdown('#ui-id-2',1)
	except Exception as e:
		print('laundry error' ,e)
	
	#parking setup
	try:
		type =[1,2]
		one_type= random.choice(type)
			
		append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(one_type))
		ju = str('$("#ui-id-3"){}'.format(append))
		
		b.script_run('$("#ui-id-3").empty();',message='parking empty')
		b.script_run(ju,message='parking append')
	except Exception as e:
		print('parking error' ,e)
	
	
	#bedrooms setup
	try:
		
			
		append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(postinfo.bed))
		ju = str('$("#ui-id-4"){}'.format(append))
		
		b.script_run('$("#ui-id-4").empty();',message='bedrooms empty')
		b.script_run(ju,message='bedrooms append')
	except Exception as e:
		print('bedrooms error' ,e)

	#bathrooms setup
	try:
		append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(postinfo.bat))
		ju = str('$("#ui-id-5"){}'.format(append))
		
		b.script_run('$("#ui-id-5").empty();',message='bathrooms empty')
		b.script_run(ju,message='bathrooms append')
	except Exception as e:
		print('bathrooms error', e)
	
	#email setup
	# time.sleep(2000)
	
	b_email = b.select_element_xpath('//*[@name="FromEMail"]','select email')
	b_email.send_keys(account_data['email'])
	nextpage = b.select_element_xpath('//*[@name="go"]','go next page')
	nextpage.click()
	#no pass click
	if 's=geoverify=' in  b.current_url():
		time.sleep(300)
	
		nextpage = b.select_element_xpath('/html/body/section/section/div[2]/div[1]/form/div/input','no pass click')
		nextpage.click()
	nextpage = b.select_element_xpath('//*[@id="leafletForm"]/button','go from map page')
	nextpage.click()
	nextpage = b.select_element_xpath('/html/body/article/section/form/button','go from image page')
	nextpage.click()
	nextpage = b.select_element_xpath('//*[@id="publish_top"]/button','go from publish page')
	nextpage.click()
	# time.sleep(120)
	
	
	
	popmail = imap(account_id,account_data['email'],account_data['password'])
	

	counter=0
	postdone = False
	
	while True:
		time.sleep(10)
		if postdone == True:
			break
			postdone = False

		counter = counter+1
		
		popmail.messages('robot@craigslist.org')
		links = popmail.get_link(['craigslist.org/pass','craigslist.org/login/onetime'])
		
			

		print('Get links')
		
		for link in links:

			conf_link = 'window.location.href = "{};'.format(link)
			b.script_run(conf_link,'link click to verify')
			
			
			
			postdone = True
			break


		
		if counter > 6:
			worker_acc.post_error(account_id,'verify link not recived')
			worker_acc.ban_3(account_id,status=2)
			print("link not recived")
			break
	
	
	if 'pass?userid=' in  b.current_url():
		#no pass click
		nextpage = b.select_element_xpath('/html/body/section/section/div[2]/div[1]/form/div/input','no pass click')
		nextpage.click()
	# check tams page
	if 's=tou' in  b.current_url():
		
		nextpage = b.select_element_xpath('//*[@id="new-edit"]/div/div[4]/div[1]/button','tams')
		nextpage.click()
	time.sleep(20)
		
	if 's=pn' in  b.current_url():
		
		#check_pva = b.select_element_xpath("//*[contains(text(),'Phone Verification)]",'no pva check')
		worker_acc.post_error(account_id,"no pva")
		worker_acc.ban_3(account_id,status=3)
	
	
	if b.try_xpath("//*[contains(text(),'View your post at')]"):
		check_post = b.select_element_xpath("//*[contains(text(),'View your post at')]",'post link check')
		worker_acc.post_done(account_id,check_post.text)
		worker_acc.post_log(account_id,b.textProxy())

	time.sleep(20)
		
	
	
	print('post done')
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
	body_mail=None
	if one_account == None or postinfo == None:
		print('post or account not find for worker')
		time.sleep(60)
		continue
	print('account last use time is : ',one_account['last_updates'])
		

	if path.isdir('profiles/' +str(one_account['id'])) == True:
		shutil.rmtree('profiles/' +str(one_account['id']))
		
	print('main')
	main(one_account,post,packages_id,body_mail)
	time.sleep(10)

		

	