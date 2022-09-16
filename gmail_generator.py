

import time
import shutil
import sys
import requests
from os import path
import random
from pyvirtualdisplay import Display
from datetime import datetime
# from ps_lib.firefox import firefoxBrowser
# from ps_lib.browser import browser

from ps_lib.uc import ucbrowser
from ps_lib.accounts import accounts
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.ps_str import ps_str
from ps_lib.imap import imap
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from number1 import number
import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))
os.path.dirname(os.path.abspath(__file__))

# from pynput.mouse import Button, Controller

def get_prices(product = 'google'):
    product = 'google'

    headers = {
        'Accept': 'application/json',
    }

    params = (
        ('product', product),
    )
    response = requests.get('https://5sim.net/v1/guest/prices', headers=headers, params=params)
    items = response.json()[product]
    for i in items:
        
        price=0
        count=0
        fastitem={}
        avarage=0
        for n in items[i].values():
            # print(n)
            price +=n['cost']
            count +=n['count']
            avarage +=1
       
        fastitem['country']=i
        fastitem['avarage ']=price/avarage
        fastitem['count']=count
        if fastitem['avarage '] <= 12:
            print(fastitem)
            print('.............................')

get_prices('google')
country=input('plz input contry name:')
pva = number('eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjY0MzYwOTEsImlhdCI6MTYzNDkwMDA5MSwicmF5IjoiY2MzNzRmNTM3MTUyMDc3MWZjODAyNWM1MTM5OWIzYWUiLCJzdWIiOjIzMTAyOH0.OOd17iPERjvtNLc6KNa15nnG5hKXvkzeBf7aJa0ApMjWoO9on4NMC4UIbJRgJ8CtVk2dk7mVi5JwzC1e_zZXis-M2sx1GsFRgWum7BIlyxhYWYYp2rAJuW7YrcAn5MWBXC7E2DaKeeVonDgwzN1_FlUAEnS1iggGgdeKtTy3YZ75mH1z3lrsjjbml_vvP2PrCdpjEl7x2EXBizng3NNxqG72rF9OwI8I5mJj1ks0oHbdMNqOdScdExG6a9MJj9NXOFQmBx9C9bTgCCkhcd1T5bmX5-royaHq8LEyZnuE9HXMwo3mHL_Nny3mwCwftC95dMUqNARrQkY5p0hK4OUQfg',country,'any','google')
def main(account_data, postinfo, packages_id, body_mail):
    # work start time
    starttime = datetime.now().strftime("%H:%M:%S")

    print(datetime.now().strftime("%H:%M:%S"))
    # print(account_data)
    account_id = account_data['id']
    worker_acc = accounts()
    use_proxy = True

    b = ucbrowser(account_id, pva=account_data)
    # b = firefoxBrowser(account_id, pva=account_data)

    time.sleep(1)
    if b.PROXY_PASS == False and b.use_proxy == True:
        b.exit()
        print('proxy condition not fulfilled')
        # worker_acc.ban_3(account_id, 5)
        time.sleep(10)
        return False

    try:

        # b.get_url('https://gmail.com')
        b.get_url('https://accounts.google.com/signup/v2/webcreateaccount?service=mail&biz=false&flowName=GlifWebSignIn&flowEntry=SignUp')
    except:
        b.exit()

    # new = b.visibil_element('xpath',
    #                         '//*[@id="yDmH0d"]/c-wiz/div/div[2]/div/div[2]/div/div[2]/div/div/div[1]/div/button/span')
                            
    # new.click()
    # new = b.visibil_element('xpath',
    #                         '//*[@id="yDmH0d"]/c-wiz/div/div[2]/div/div[2]/div/div[2]/div/div/div[2]/div/ul/li[1]/span[2]')
    # new.click()
    firstName = b.visibil_element('id', "firstName")
    name = account_data['post_data'].split("-")
    
    print('first name typing')
    for character in name[0]:
        firstName.send_keys(character)
        # time.sleep(1)
    lastName = b.visibil_element('id', "lastName")
    print('last name typing')
    for character in name[1]:
        lastName.send_keys(character)
        # time.sleep(1)
    username = b.visibil_element('id', "username")
    print('username typing')

    for character in name[0]+name[1]:
        username.send_keys(character)
        # time.sleep(1)
    time.sleep(5)
    if b.visibil_element('css', 'button[data-username]'):
        ConfirmUsername = b.visibil_element('css', 'button[data-username]')
        ConfirmUsername.click()
    Passwd = b.visibil_element('css', '[name="Passwd"]')
    print('Passwd typing')
    for character in account_data['extra']:
        Passwd.send_keys(character)
        # time.sleep(2)
    ConfirmPasswd = b.visibil_element('css', '[name="ConfirmPasswd"]')
    for character in account_data['extra']:
        ConfirmPasswd.send_keys(character)
        # time.sleep(2)
    if b.visibil_element('css', 'button[data-username]'):
        ConfirmUsername = b.visibil_element('css', 'button[data-username]')
        ConfirmUsername.click()
    

    nextpage = b.visibil_element('xpath',
                                '/html/body/div[1]/div[1]/div[2]/div[1]/div[2]/div/div/div[2]/div/div[2]/div/div[1]/div/div/button')
    nextpage.click()
    

    
    buy_number = pva.buy_number()
    country_code = pva.country_c
    print(buy_number)

    put_number = b.visibil_element('xpath',"//div[@class='Ufn6O UOZHQ']//label")
    put_number.send_keys('{0}'.format(country_code))
    put_number.send_keys('{0}'.format(buy_number))
    
    next_page = b.visibil_element('xpath',"//button[@type='button']//span")
    next_page.click()

    try:
        set_code = b.visibil_element('xpath',"//input[@class='whsOnd zHQkBf']")
        if set_code:
            check_sms = pva.check_sms()
            set_code.send_keys("{0}".format(check_sms))
            time.sleep(2)
            next_page = b.visibil_element('xpath',"//button[@type='button']//span")
            next_page.click()
        
    except:
        pva.ban_number()
    mailinfo=''
    newgmail = b.visibil_element('css', '[data-profile-identifier]')
    if newgmail:
        gmail = newgmail.get_attribute("data-email")
        mailinfo += gmail
        mailinfo += ':'+account_data['extra']
        mailinfo += ':'+account_data['email']
        print(mailinfo)
        recoveryEmail = b.visibil_element('css', '[name="recoveryEmail"]')
        recoveryEmail.send_keys(account_data['email'])

        day = b.visibil_element('css', '[name="day"]')
        day.send_keys(23)

        month = b.visibil_element('id',"month")
        mdb = Select(month)
        mdb.select_by_index(random.randint(0,11))

        year = b.visibil_element('css', '[name="year"]')
        year.send_keys(random.randint(1980,2007))

        gender = b.visibil_element('id',"gender")
        gd = Select(gender)
        gd.select_by_index(random.randint(1,2))

        clr_ele = b.driver.find_element(By.XPATH,("//div[@class='Ufn6O UOZHQ']//label/input"))
        clr_ele.clear()
        finalbutton = b.driver.find_element(By.XPATH,("//button[@type='button']//span"))
        finalbutton.click()
        print('others option')
        time.sleep(10)
        # btnIagree = b.visibil_element('xpath','//*[@id="view_container"]/div/div/div[2]/div/div[2]/div/div[1]/div/div/button')
        btnGroup = b.driver.find_element(By.XPATH,'//*[@id="view_container"]/div/div/div[2]/div/div[2]')
        b.scroll_like_user(btnGroup)
        btnIagree = btnGroup.find_element(By.TAG_NAME,'button')
        
        
        
       
        
        
        try:
            btnIagree.click()
            f = open("gmail.txt", "a")
            f.write(mailinfo)
            f.close()
            time.sleep(20)
            
            # ActionChains(b.driver).move_to_element(btnGroup).click(btnIagree).perform()
        except Exception as e:
            # print(e)
            time.sleep(100)
        # btnIagree.click()
        time.sleep(200)
    else:
        

        print('varify need')

    worker_acc.post_error(account_id, "action try", software_type='GmailCreator')
    #title="thanks for flagging!"
    # b.wait('//*[@title="thanks for flagging!"]')

    b.ipinfo_save(software_name='gmail creator')

    b.exit()
    print('browser close')

    print('start :', starttime)
    print('end :', datetime.now().strftime("%H:%M:%S"))


setup = table()
setup.token_verify()
# setup.pop_verify()

#w = int(input('how much worker you need? '))
# packages_id = input('proxy info by a line : ')
packages_id = '317345'

# worker = w + 1
worker = 2
# ........................start worker....................
# open('active.txt', "w+")
utility = helper()
headers = {}
profile_ids = {}
acc = accounts()
# print(acc.get_proxy_list())
# exit()
post = post()
if sys.platform not in ['Windows', 'win32', 'cygwin']:
    display = Display(visible=0, size=(1024, 768))
    display.start()
# x = threading.Thread(target=smtp.reply_check, args=(1,), daemon=True)
# x.start()
while True:

    # subprocess.call(["sudo", "ifconfig", "ens33", "down"])
    # subprocess.call(["sudo", "ifconfig", "ens33", "hw",
    #                 "ether", "00:11:22:33:44:55"])
    # subprocess.call(["sudo", "ifconfig", "ens33", "up"])
    # utility.network_check()
    if setup.token_off():
        print('software off now but reply checking runing')
        time.sleep(60)
        continue
    one_account = acc.get_account()

    postinfo = post.get_post()
    body_mail = None
    if one_account == None or postinfo == None:
        print('post or account not find for worker')
        time.sleep(60)
        continue
    print('account id : ', one_account['id'])

    if path.isdir('profiles/' + str(one_account['id'])) == True:
        shutil.rmtree('profiles/' + str(one_account['id']))

    print('main')
    main(one_account, post, packages_id, body_mail)
    time.sleep(1)