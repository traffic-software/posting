import sqlite3

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


