import sqlite3
from sys import exit
class post:
	def __init__(self):
		self.conn = sqlite3.connect('data/databases.db')
	def get_post(self):

		c = self.conn.cursor()
		# c.execute("SELECT * FROM account WHERE runing = 0")
		sql = "SELECT * FROM posts  ORDER BY random() LIMIT " + str(1)
		c.execute(sql)
		post =c.fetchone()
		return self.get_formated_data(c.description,post)
	
	def get_body_mail(self):

		try:
			c = self.conn.cursor()
			# c.execute("SELECT * FROM account WHERE runing = 0")
			sql = "SELECT * FROM settings  WHERE name = 'mail' ORDER BY random() LIMIT 1" 
			c.execute(sql)
			mail =c.fetchone()
			
			m= self.get_formated_data(c.description,mail)
			return m['value']
		except:
			return None
	
	def delete_all(self):

		c = self.conn.cursor()
		sql = "DELETE FROM posts"
		c.execute(sql)
		post =c.fetchone()
		return self.get_formated_data(c.description,post)

	def insert(self, combos):
		c = self.conn.cursor()
		c.executemany("INSERT INTO posts (subject,body) VALUES  (?,?)", combos)
		self.conn.commit()

	def save(self):
		my_file = open('post.txt', 'r+')
		lines = my_file.readlines()
		my_file.truncate(0)
		my_file.close()
		list_data = []
		if len(lines)>10:
			self.delete_all()
		for line in lines:


			data = line.split(":")
			if 1 < len(data):
				post = (data[0],data[1].rstrip("\n"))
				list_data.append(post)
		self.insert(list_data)

	def get_formated_data(self,headers,data):
		try:
			data = dict(zip([c[0] for c in headers], data))
		except:
			data = None
		return data


