from datetime import date
from datetime import timedelta
import mysql.connector
import datetime

today = datetime.datetime.now()
# print(today)
# today = date.today()
# print(today)
mydb = mysql.connector.connect(
host="localhost",
user="root",
password="",
database="linkdin"
)

mycursor = mydb.cursor()
query = "SELECT * FROM sms_no"
mycursor.execute(query)
cookie = mycursor.fetchone()
# print(cookie[5])
# print(cookie[6])
# print(cookie[7])


today = datetime.datetime.now()
yesterday = today - timedelta(days = 1)
print(yesterday)












# query = "SELECT * FROM sms_lead WHERE processing_completed=0 LIMIT 5"
# mycursor.execute(query)
# myresult = mycursor.fetchone()
# print(myresult[0])

# query = "SELECT * FROM sms_message WHERE type=1"
# mycursor.execute(query)
# add_a_note_query = mycursor.fetchone()
# print(add_a_note_query[0])
# print(add_a_note_query)

# query = "SELECT * FROM sms_message WHERE type=1"
# mycursor.execute(query)
# sms_message_q = mycursor.fetchone()
# sent_msg = sms_message_q[4]                

# query = "SELECT * FROM sms_no"
# mycursor.execute(query)
# msg_query = mycursor.fetchone()
# cookie_id = msg_query[0]
# sql = "INSERT INTO recivemessage (no_id, sms_lead_id,eventType,message_type,message_id,body) VALUES (%s, %s, %s, %s, %s, %s)"
# val = ("{0}".format(cookie_id), "{0}".format(myresult[0]),"out","{0}".format(sms_message_q[3]),"{0}".format(sms_message_q[0]),"{0}".format(sms_message_q[2]))
# mycursor.execute(sql, val)
# mydb.commit()
# print("-----------------------Sent message Insert receive table is done----------------")