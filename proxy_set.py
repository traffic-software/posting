import sqlite3
databessname = 'databases'   #randomString(10)
conn = sqlite3.connect('data/'+databessname+".db")
def ps_proxys_insert(conn, proxys):

    c = conn.cursor()

    c.executemany("INSERT INTO proxys (data,checked) VALUES  (?,?)",proxys)
    conn.commit()



def ps_proxys_save():

    with open('proxy.txt',encoding="utf8") as my_file:
        lines = my_file.readlines()
        #print(lines)
        #print(type(lines))
    list_data=[]
    for key,line in enumerate(lines):


        ps_data =line.rstrip("\n")
        #.split(":")
        #print(ps_data)

        #host = ps_data[0]
        #port = ps_data[1].rstrip("\n")
        proxy_tada = (ps_data,0) #(host+":"+port,0)
        list_data.append(proxy_tada)
    ps_proxys_insert(conn, list_data)
ps_proxys_save()