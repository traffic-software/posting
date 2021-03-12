import threading
from selenium.webdriver.common.keys import Keys
import time
import sqlite3
from ps_lib.browser import browser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper

# driver = webdriver.PhantomJS()
# driver.get('https://python.org')
# print(driver.current_url)
# driver.get('https://google.com')
# print(driver.current_url)
# exit()
w = int(input('how much worker you need? '))
worker = w + 1

conn = sqlite3.connect("data/databases.db")





def main(account_data):
	# print(account_data)
	account_id = threading.currentThread().getName()
	account = psThread(account_id)
	# print(str(account_id) + "\t" + str(account_data))
	ps_data = account_data.split(":")
	user_mail = ps_data[0]
	user_password = ps_data[1]
	# print(user_mail)
	lovoo = browser()

	assert "LOVOO" in lovoo.get_url("https://www.lovoo.com")
	ifrem = lovoo.select_element("#gdpr-consent-notice")
	time.sleep(5)
	print(lovoo.get_title())

	lovoo.iframe(ifrem)
	time.sleep(5)
	print(lovoo.get_title())

	el =lovoo.select_element("#save")
	time.sleep(5)
	el.click()
	time.sleep(5)
	lovoo.switch_back()
	time.sleep(5)
	print(lovoo.get_title())



	el = lovoo.select_element('[data-automation-id~="login-button"]')
	# data-automation-id="login-button"
	# <span _ngcontent-hpb-c7="">Accept All</span>
	el.click()
	email = lovoo.select_element('[name="authEmail"]')
	# data-automation-id="login-enter-email-input"
	# name="authEmail"

	email[0].send_keys(user_mail)
	password = lovoo.select_element('[name="authPassword"]')
	# name="authPassword"

	password[0].send_keys(user_password)
	time.sleep(1)
	btnLogin = lovoo.select_element('[ng-click="doLogin()"]')

	btnLogin[0].send_keys(Keys.RETURN)
	# Login: Incorrect entry
	# loginEroor = driver.find_element_by_css_selector("")
	time.sleep(5)
	for i in range(3):
		print('for i in renge {0}'.format(i))
		time.sleep(10)
		try:
			messenger = lovoo.select_element('[ng-click="openChatDialog()"]')

			if messenger.is_enabled():
				messenger.click()
			else:
				time.sleep(20)
				messenger.click()
		except:
			print('eroor in: [ng-click="openChatDialog()"]')

		time.sleep(10)
		try:
			list_items = lovoo.select_element('[id^="conversation"]')
			print(len(list_items))
		except:
			print(' eroor in: [id^="conversation"]')

			lovoo.quit()
			f = open('active.txt', 'a')
			f.writelines(account_id + "\n")
			continue

		for list_item in list_items:
			print('\n............ list_item : worker id {0}................'.format(account_id))

			try:
				time.sleep(2)

				list_item.click()

				time.sleep(2)

				user_id_info = list_item.get_attribute("id")
				user_id = user_id_info.replace("conversation-list-", "")
				# conversation-list-
				user_name = lovoo.select_element('[ng-bind-html="selectedConversation.user.name"]')

				last_message = lovoo.select_element('[class="break-word small"]')[-1]
				if "LOVOO" in last_message.text:
					continue
				profile_id = lovoo.select_element('[ng-if="message.hasProfilePicture"]')[-1]
				if '4ecce5afebf2' in user_id:
					# 4ecce5afebf2c80506000025
					print('suport')
					continue

				if '/sel' in profile_id.get_attribute('href'):
					print('bot message\n............................')
					continue

				else:

					time.sleep(2)
					print('username: ' + user_name.text + ' user id: ' + user_id)
					lovoo.ps_message_box(account, user_id, user_name.text)
					closs = lovoo.select_element('[class="modal-dialog"] > div > div > [ng-click="$close()"]')
					if closs.is_enabled():
						closs.click()



			except:
				print(' eroor in: selectedConversation')

		print('loop count ' + str(i))
		if i == 2:
			lovoo.quit()
			f = open('active.txt', 'a')
			f.writelines(account_id + "\n")
		else:
			lovoo.refresh()
	# driver.execute_script("location.reload()")


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

while True:
	acc = accounts()
	acc.save()

	if worker > threading.active_count():

		one_account = acc.get_account()
		if one_account == None:
			time.sleep(10)
			acc.get_account_for_inactive()

			continue
		acc.account_active(one_account[0])

		t = threading.Thread(target=main, args=(one_account[1],))
		acc.account_active(one_account[0])

		threads.append(t)
		t.setName(one_account[0])
		t.start()
		time.sleep(50)

	else:

		print('..............active thread :' + str(threading.active_count()) + '...............')
		time.sleep(50)
