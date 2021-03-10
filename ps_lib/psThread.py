from os import path
import sqlite3
class psThread:
	def __init__(self,dbName):
		self.db = dbName
		if self.dbfile():
			self.conn = sqlite3.connect('data/' + self.db + ".db")

		else:
			self.conn = sqlite3.connect('data/' + self.db + ".db")
			self.ps_tebl_insert(self.db)




	def dbfile(self):
		if path.exists('data/' + self.db + ".db"):
			return True

		else:
			open('data/' + self.db + ".db", "w+")
			return False

	def ps_tebl_insert(self,dbName):
		c = self.conn.cursor()
		c.execute(
			"CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, runing INTEGER DEFAULT 0)")
		c.execute(
			"CREATE TABLE IF NOT EXISTS conversation (id INTEGER PRIMARY KEY AUTOINCREMENT, acc INTEGER NOT NULL DEFAULT 0, name TEXT NOT NULL DEFAULT 0, chat_id TEXT NOT NULL DEFAULT 0,send INTEGER DEFAULT 0)")
		self.conn.commit()
		return True

	def get_messsage(self, chat_id, name):
		chat_info = self.get_chat_info(chat_id)
		if chat_info == None:
			self.chat_insert(chat_id, name)
			chat_info = self.get_chat_info(chat_id)

		else:
			chat_info = self.get_chat_info(chat_id)

		self.conn.commit()
		if chat_info[4] > 2:
			return None
		else:
			mess_no = chat_info[4] + 1
			self.update_tbl("conversation", "send", mess_no, "id", chat_info[0])
			return self.message_info(chat_info[4])

	def message_info(self,mess_no):

		lines = open('messes.txt', "r").readlines()
		print('messasge no: ' + str(mess_no))
		# message = text.readline(mess_no)

		return lines[int(mess_no)]

	def get_chat_info(self, chat_id):
		c = self.conn.cursor()
		sql = "SELECT * FROM conversation WHERE chat_id = '{}'".format(str(chat_id))

		c.execute("SELECT * FROM conversation WHERE chat_id =?", (str(chat_id),))
		# c.execute("SELECT * FROM account WHERE id = "+id+" ORDER BY random() LIMIT 1")
		chat_info = c.fetchone()
		return chat_info

	def chat_insert(self, chat_id, name):
		c = self.conn.cursor()
		sql = "INSERT INTO conversation (chat_id,name) VALUES  ('" + str(chat_id) + "','" + str(name) + "')"

		c.execute(sql)

		self.conn.commit()
		return 'insert'

	def update_tbl(self, tbl, row, velu, where, where_velu):
		c = self.conn.cursor()
		sql = "UPDATE {0} SET {1} = {2} WHERE {3} = {4}".format(tbl, row, velu, where, where_velu)
		c.execute(sql)
		self.conn.commit()
		return 'ok'

	def insert(self,combos):
		c = self.conn.cursor()
		sql = "INSERT INTO account (data,runing) VALUES  ({0},1)".format(combos)
		# print(sql)
		c.execute(sql)
		self.conn.commit()
		return c.lastrowid

	def get_account(self, id):
		c = self.conn.cursor()
		sql = "SELECT * FROM account WHERE id = " + id
		c.execute(sql)
		# c.execute("SELECT * FROM account WHERE id = "+id+" ORDER BY random() LIMIT 1")
		a = c.fetchall()
		# c.fetchall()
		# c.fetchmany()()
		# c.fetchone()
		self.conn.commit()
		return a