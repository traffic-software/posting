import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# from pyvirtualdisplay import Display
import pathlib
import requests
import winreg
import json
from os import path
import shutil
import os
import re
import time
from datetime import datetime
import random
import sqlite3
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
driver_path = 'chromedriver.exe'


while True:
    mail_status = 1
    print('...............start...............')
    workSart = datetime.strptime(
        datetime.now().strftime("%H:%M:%S"), "%H:%M:%S")
    print(workSart)
    all = gmail()

    id = all['id']
    email_address = all['email']
    email_address = str(email_address)
    email_pass = all['password']
    recovery_email = all['password']
    new_pass = ran_password()

    recovery_email_new = recovery_return(recovery_email)
    send_keys = True
    print("number or email: ", email_address)

    login_value = gmail_login(email_address,
                              email_pass, recovery_email, id)
    # https://myaccount.google.com/signinoptions/rescuephone?rapt=AEjHL4O6fe_EfAiXXVaPcwDTlTWYr_CkaZyl05qeynmAWeCy3I2gWUtrXL-g_2LAw1dcEsQykM-58CaCSOclZG6fZ-mcjF3XmQ
    # print(login_value)
    # time.sleep(60)
    # if login_value == "Capture":
    #     print("CAPTURE")
    #     driver.close()
    #     time.sleep(60)
    #     continue

    if login_value == True:
        chengePassRq = req_change_password(driver, id)
        # print('mail_status', login_value)
        # bell = visibil_element(
        #     driver, 'xpath', ("//img"), 2)
        # if bell:
        #     gmail_fail_update(5, id)
        #     continue

        driver.implicitly_wait(10)
        email_address = language_cng(driver, id, email_pass)
        print('new rec:', recovery_email_new)
        update_recovery(driver, email_address, recovery_email_new, id)
        if chengePassRq == False:
            change_password(driver, email_address, new_pass, id)
        remove_number(driver, id)
        device_activity(driver)

        find_time(driver, email_address, id)
        activity_login(driver)

        gmail_update(id)
    else:
        print(login_value)

    try:
        # print('not login')
        driver.delete_all_cookies()
        # driver.close()
    except Exception as e:
        print(e)
        pass
    driver.close()
    workEnd = datetime.strptime(
        datetime.now().strftime("%H:%M:%S"), "%H:%M:%S")
    workTime = workEnd-workSart
    print(
        f"work no {email_address} prosses time: {workTime.total_seconds()} seconds")
    # print('...............end...............')
