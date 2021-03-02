import sqlite3
databessname = 'databases'#randomString(10)
conn = sqlite3.connect('data/'+databessname+".db")
def ps_combos_insert(conn, combos):
    c = conn.cursor()
    c.executemany("INSERT INTO account (data,runing) VALUES  (?,?)", combos)
    conn.commit()
def ps_combos_save():

    with open('account.txt', encoding="utf8") as my_file:
        lines = my_file.readlines()
        #print(lines)
        #print(type(lines))
    list_data = []
    for key, line in enumerate(lines):
        print(line)

        ps_data = line.split(":")
        username = ps_data[0]
        password = ps_data[1].rstrip("\n")
        combos_tada = (username+":"+password, 0)
        list_data.append(combos_tada)
    ps_combos_insert(conn, list_data)
ps_combos_save()