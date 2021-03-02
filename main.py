import threading
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium import webdriver
import time
import sqlite3
from os import path
import os
w = int(input('how much worker you need? '))
worker =w+1
from threading import Thread
import json
conn = sqlite3.connect("data/databases.db")
def get_accounts(conn):
	c = conn.cursor()
	#c.execute("SELECT * FROM account WHERE runing = 0")
	sql = "SELECT * FROM account WHERE runing = 0 ORDER BY random() LIMIT "+str(w)
	c.execute(sql)
	account = c.fetchall()
	#c.fetchall()
	#c.fetchmany()()
	#c.fetchone()
	conn.commit()
	return account
def get_account(conn):
	c = conn.cursor()
	#c.execute("SELECT * FROM account WHERE runing = 0")
	c.execute("SELECT * FROM account WHERE runing = 0 ORDER BY random() LIMIT 1")
	account = c.fetchone()
	#c.fetchall()
	#c.fetchmany()()
	#c.fetchone()
	conn.commit()
	return account
def ps_account_insert_thred(nameDb, combos):
	c = nameDb.cursor()
	sql = "INSERT INTO account (data,runing) VALUES  ({0},1)".format(combos)
	#print(sql)
	c.execute(sql)
	nameDb.commit()
	return c.lastrowid
def get_account_thred(profilDB,id):
	#print("SELECT * FROM account WHERE runing = "+id)
	c = profilDB.cursor()
	sql = "SELECT * FROM account WHERE runing = "+id
	c.execute(sql)
	#c.execute("SELECT * FROM account WHERE id = "+id+" ORDER BY random() LIMIT 1")
	account = c.fetchall()
	#c.fetchall()
	#c.fetchmany()()
	#c.fetchone()
	profilDB.commit()
	#print(account)
	return account
def account_active(id):
	c = conn.cursor()
	# c.execute("SELECT * FROM account WHERE runing = 0")
	sql = "UPDATE account SET runing =1 WHERE id = "+str(id)
	c.execute(sql)
	conn.commit()
def all_account_active():
	c = conn.cursor()
	# c.execute("SELECT * FROM account WHERE runing = 0")
	sql = "UPDATE account SET runing =0 WHERE runing =1"
	c.execute(sql)
	conn.commit()
def all_account_delete():
	c = conn.cursor()
	# c.execute("SELECT * FROM account WHERE runing = 0")
	sql = "DELETE FROM account"
	c.execute(sql)
	conn.commit()

def get_account_for_inactive():
	file = open('active.txt',"r+")
	lines = file.readlines()

	file.truncate()

	print(lines)
	# print(type(lines))
	list_data = []
	for line in lines:
		account_id = line.rstrip("\n")
		account_inactive(account_id)
		open('active.txt', "w+")


def account_inactive(id):
	c = conn.cursor()
	# c.execute("SELECT * FROM account WHERE runing = 0")
	sql = "UPDATE account SET runing =0 WHERE id = "+str(id)
	c.execute(sql)
	conn.commit()
def account_ban(id):
	c = conn.cursor()
	# c.execute("SELECT * FROM account WHERE runing = 0")
	sql = "UPDATE account SET runing =2 WHERE id = "+str(id)
	c.execute(sql)
	conn.commit()


def Create_db(dbName):
	if path.exists('data/' +dbName+".db"):
		print('db file exists')
	else:
		open('data/'+dbName+".db","w+")
		ps_tebl_insert(dbName)
	return sqlite3.connect('data/' + dbName + ".db")
def ps_tebl_insert(dbName):
	dbName = sqlite3.connect('data/' + dbName + ".db")
	c = dbName.cursor()
	c.execute("CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, runing INTEGER DEFAULT 0)")
	c.execute("CREATE TABLE IF NOT EXISTS conversation (id INTEGER PRIMARY KEY AUTOINCREMENT, acc INTEGER NOT NULL DEFAULT 0, name TEXT NOT NULL DEFAULT 0, chat_id TEXT NOT NULL DEFAULT 0,send INTEGER DEFAULT 0)")
	dbName.commit()
	return True
def get_messsage(dataDB, chat_id, name):
	chat_info = get_chat_info(dataDB, chat_id)
	if chat_info == None:
		chat_insert(dataDB, chat_id, name)
		chat_info = get_chat_info(dataDB, chat_id)

	else:
		chat_info = get_chat_info(dataDB, chat_id)

	dataDB.commit()
	if chat_info[4] > 2:
		return None
	else:
		mess_no = chat_info[4] +1
		update_tbl(dataDB, "conversation", "send", mess_no, "id", chat_info[0])
		return message_info(chat_info[4])
def message_info(mess_no):



	lines  = open('messes.txt', "r").readlines()
	print('messasge no: '+str(mess_no))
	#message = text.readline(mess_no)

	return lines[int(mess_no)]


def update_tbl(conn, tbl, row, velu, where,where_velu):
	c = conn.cursor()
	sql = "UPDATE {0} SET {1} = {2} WHERE {3} = {4}".format(tbl,row,velu,where,where_velu)
	c.execute(sql)
	conn.commit()
	return 'ok'

def get_chat_info(dataDB,chat_id):
	c = dataDB.cursor()
	sql = "SELECT * FROM conversation WHERE chat_id = '{}'".format(str(chat_id))

	c.execute("SELECT * FROM conversation WHERE chat_id =?",(str(chat_id),))
	# c.execute("SELECT * FROM account WHERE id = "+id+" ORDER BY random() LIMIT 1")
	chat_info = c.fetchone()
	return chat_info
def chat_insert(dataDB,chat_id,name):
	c = dataDB.cursor()
	sql = "INSERT INTO conversation (chat_id,name) VALUES  ('"+str(chat_id)+"','"+str(name)+"')"



	c.execute(sql)

	dataDB.commit()
	return 'insert'


def ps_message_box(driver,dataDB, chat_id, name,):
	#try:
	#messenge_box = driver.find_element_by_tag_name('textarea')
	messenge_box = driver.find_element_by_css_selector('[placeholder = "Your message"]')

	#messenge_box = driver.find_elements_by_css_selector('[placeholder = "Your message"]')
	messenge_box.click()
	for character in get_messsage(dataDB,chat_id,name):
		messenge_box.send_keys(character)
		time.sleep(0.1)

	time.sleep(2)
	send_buton = driver.find_element_by_css_selector('[ng-click="sendMessage()"]')
	send_buton.click()
	time.sleep(5)
	#except:
	print('eroor in: [ng-click="openChatDialog()"]')

def main(account_data):
	#print(account_data)
	account_id = threading.currentThread().getName()
	profilDB = Create_db(account_id)
	#print(str(account_id) + "\t" + str(account_data))
	ps_data = account_data.split(":")
	user_mail = ps_data[0]
	user_password = ps_data[1]
	#print(user_mail)
	options = Options()
	fp = FirefoxProfile()
	driver = webdriver.Firefox(firefox_profile=fp)
	#driver = webdriver.Firefox()
	driver.get("https://www.lovoo.com")
	assert "LOVOO" in driver.title
	time.sleep(5)

	elem = driver.find_element_by_css_selector('[data-automation-id~="login-button"]')
	# data-automation-id="login-button"
	elem.click()
	time.sleep(2)

	email = driver.find_elements_by_css_selector('[name="authEmail"]')
	#data-automation-id="login-enter-email-input"
	# name="authEmail"

	email[0].send_keys(user_mail)
	password = driver.find_elements_by_css_selector('[name="authPassword"]')
	# name="authPassword"

	password[0].send_keys(user_password)
	time.sleep(1)
	btnLogin = driver.find_elements_by_css_selector('[ng-click="doLogin()"]')

	btnLogin[0].send_keys(Keys.RETURN)
	#Login: Incorrect entry
	#loginEroor = driver.find_element_by_css_selector("")
	time.sleep(5)
	for i in range(3):
		print('for i in renge {0}'.format(i))
		time.sleep(10)
		try:
			messenger = driver.find_element_by_css_selector('[ng-click="openChatDialog()"]')

			if messenger.is_enabled():
				messenger.click()
			else:
				time.sleep(20)
				messenger.click()
		except:
			print('eroor in: [ng-click="openChatDialog()"]')



		time.sleep(10)
		try:
			list_items = driver.find_elements_by_css_selector('[id^="conversation"]')
			print(len(list_items))
		except:
			print(' eroor in: [id^="conversation"]')

			driver.quit()
			f = open('active.txt', 'a')
			f.writelines(account_id+"\n")
			continue



		for list_item in list_items:
			print('\n............ list_item : worker id {0}................'.format(account_id))

			try:
				time.sleep(2)

				list_item.click()


				time.sleep(2)


				user_id_info = list_item.get_attribute("id")
				user_id = user_id_info.replace("conversation-list-","")
				#conversation-list-
				user_name = driver.find_element_by_css_selector('[ng-bind-html="selectedConversation.user.name"]')

				last_message = driver.find_elements_by_css_selector('[class="break-word small"]')[-1]
				if "LOVOO" in last_message.text:
					continue
				profile_id = driver.find_elements_by_css_selector('[ng-if="message.hasProfilePicture"]')[-1]
				if '4ecce5afebf2' in user_id:
					#4ecce5afebf2c80506000025
					print('suport')
					continue

				if '/sel' in profile_id.get_attribute('href'):
					print('bot message\n............................')
					continue

				else:

					time.sleep(2)
					print('username: ' + user_name.text + ' user id: ' + user_id)
					ps_message_box(driver,profilDB,user_id,user_name.text)
					closs = driver.find_element_by_css_selector('[class="modal-dialog"] > div > div > [ng-click="$close()"]')
					if closs.is_enabled():
						closs.click()



			except:
				print(' eroor in: selectedConversation')

		print('loop count '+str(i))
		if i ==2:
			driver.quit()
			f = open('active.txt', 'a')
			f.writelines(account_id+"\n")
		else:
			driver.refresh()
		#driver.execute_script("location.reload()")


# ........................start worker....................
#ng-click="doLogin()"
mess1 = "how are you?"
mess2 = "where are you from"
mess3 = "Basically I don't use lovoo all the time, let's talk about it in the mail"
#driver.get("https://www.lovoo.com")
#driver.close()
open('active.txt', "w+")
all_account_active()
accounts =get_accounts(conn)
threads = []
headers = {}
profile_ids = {}
pid = threading.local()


while True:





	if worker > threading.active_count():

		one_account = get_account(conn)
		if one_account == None:
			time.sleep(10)
			get_account_for_inactive()

			continue
		account_active(one_account[0])



		t = threading.Thread(target=main, args=(one_account[1],))
		account_active(one_account[0])

		threads.append(t)
		t.setName(one_account[0])
		t.start()
		time.sleep(50)

	else:

		print('..............active thread :'+str(threading.active_count())+'...............')
		time.sleep(50)



