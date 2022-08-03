import sqlite3
from sys import exit
from ps_lib.ps_setup import table
import requests
import time


class helper:

    def __init__(self):
        self.software = table()
        self.db = sqlite3.connect(self.software.databasesfile)

    def network_check(self):

        while True:
            try:
                r = requests.get('https://api.myip.com', timeout=1)
                break
            except:
                print('network_check : plz check your  network connection')
                time.sleep(10)
                continue
