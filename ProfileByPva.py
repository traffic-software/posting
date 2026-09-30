from ast import Not
from email.policy import SMTP
from re import sub
import threading
import time
import shutil
import random
import string
import fnmatch
import sys
from os import path
# from pyvirtualdisplay import Display
from datetime import datetime
import smtp
from ps_lib.uc import ucbrowser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.ps_str import ps_str
from ps_lib.imap import imap
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import os
import pyautogui

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))
print(bundle_dir)


def main(account_data, postinfo, packages_id, body_mail):
    # work start time
    starttime = datetime.now().strftime("%H:%M:%S")

    print(datetime.now().strftime("%H:%M:%S"))

    account_id = account_data['id']
    print("account id: ", account_id)
    worker_acc = accounts()

    settings = table()
    popacc = settings.pop_verify()

    if "yes" == settings.pva_verify():
        str(input("type any key to start make pva : "))
    pp = "pva_pop" == popacc
    if not pp:
        pop = popacc.split(":")
        popmail = imap(account_id, pop[0], pop[1])
    else:
        popmail = imap(
            account_id, account_data['email'], account_data['password'])

    popmail.messages()
    
    popmail.close()
    profile_dir=bundle_dir+"\{0}\{1}".format("profiles",str(one_account['id']))
    if path.isdir(bundle_dir+"\{0}\{1}".format("profiles",str(one_account['id']))) == False:
    
        profile_dir=bundle_dir+"\{0}\{1}".format("profiles",str(one_account['id']))
        # extension_dir=bundle_dir+"\{0}\{1}".format("extension",str(one_account['id']))
        
        print(profile_dir)
    extension_dir = os.path.join(*[bundle_dir,"extension", str(one_account['id'])])
    if path.isdir(bundle_dir+"\{0}\{1}".format("extension",str(one_account['id']))) == False:
        extension_dir = os.path.join(*[bundle_dir,"extension", str(one_account['id'])])
        print(extension_dir)
        os.mkdir(extension_dir)
    b = ucbrowser(account_id, pva=account_data,profile_dir=profile_dir, image_bock=False,use_proxy=True)
    time.sleep(5)
    if b.PROXY_PASS == False:
        b.exit()
        print('proxy condition not fulfilled')
        # worker_acc.ban_3(account_id, 5)
        time.sleep(10)
        return False
    url = 'https://{0}'.format(account_data['extra'])
    b.get_url(url)
    time.sleep(10)
    
    b.get_url('https://accounts.craigslist.org/login/home')
    loginuser = b.driver.execute_script(
    """return document.evaluate('//*[contains(text(),"most recent")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")

    # if loginuser:
    #     #login user
    #     input('login user')
    #     pass
    #check not login user 
    notloginUser=b.driver.execute_script("""return document.evaluate('//*[contains(text(),"Email / Handle")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    if notloginUser:
        #not login user
        
        pva = b.driver.execute_script("""return document.evaluate('//*[@id="inputEmailHandle"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
        # pva = b.select_element_xpath('//*[@id="inputEmailHandle"]', 'type pva')
        print('pva text typing')
        for character in account_data['email']:
            pva.send_keys(character)
            time.sleep(random.choice([0.1, 0.3, 0.2, 0.4, 0.5]))
        print('pva text typing done')
        onetimeLink = b.driver.execute_script("""return document.evaluate('//*[@id="onetime"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
        # onetimeLink = b.select_element_xpath('//*[@id="onetime"]', 'onetime link sent')
        onetimeLink.click()
        

        counter = 0
        linkcheck = False

        while True:
            time.sleep(10)
            if linkcheck == True:
                break
                

            counter = counter+1
            if not pp:
                pop = popacc.split(":")
                popmail = imap(account_id, pop[0], pop[1])
            else:
                popmail = imap(account_id, account_data['email'], account_data['password'])
            popmail.messages()
            links = popmail.get_link(
                ['craigslist.org/pass', 'craigslist.org/login/onetime'])

            print('Get links')

            for link in links:

                conf_link = 'window.location.href = "{};'.format(link)
                b.script_run(conf_link, 'link click to verify')

                linkcheck = True
                break
            popmail.close()
            
        

       
        # input('not login user')


    acc_post_datas = False
    if account_data['post_data'] is not None:
        acc_post_datas = account_data['post_data'].split("-")
    else:
        print('acc post data is none')

    try:
        
        url = 'https://{0}'.format(account_data['extra'])
        
        if acc_post_datas:
            url = 'https://'+acc_post_datas[0]

        b.get_url(url)
    except:
        b.exit()

    newPostLink = b.driver.execute_script("""return document.evaluate('//*[contains(text(),"post an ad")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    newPostLink.click()
    # b.scroll_like_user(button)
    # time.sleep(random.choice([1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30]))
    

    # https://post.craigslist.org/k/sib7px0t7BGflPX08yY-RA/Qdjqi?s=subarea
    if 'subarea' in b.current_url():
        sub_aria = b.driver.find_elements(By.CSS_SELECTOR,"input[type=radio]")
        
        sub_aria = random.choice(sub_aria)
        # b.scroll_like_user(sub_aria)

        sub_aria.click()
    if 's=hood' in b.current_url():
        sub_aria = b.driver.find_elements(By.CSS_SELECTOR,"input[type=radio]")
        sub_aria = random.choice(sub_aria)
        # b.scroll_like_user(sub_aria)

        sub_aria.click()
    housingoffered = b.driver.execute_script("""return document.evaluate('//*[contains(text(),"housing offered")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    housingoffered.click()
    # b.scroll_like_user(button)
    
    apartments= b.driver.execute_script("""return document.evaluate('//*[contains(text(),"apartments / housing for rent")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    apartments.click()
    # b.scroll_like_user(button)
    

    # Posting Title setup
    b_sub = b.driver.execute_script("""return document.evaluate('//*[@id="PostingTitle"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")

    postsub = ps_str(postinfo.getdata('data1'))
    print('b_sub text typing')
    for character in postsub.Spin():
        b_sub.send_keys(character)
    print('b_sub text typing done')
    city = b.driver.execute_script("""return document.evaluate('//*[@id="geographic_area"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    # b.scroll_like_user(postal_code)
    neighborhood = b.proxy_city if postinfo.getdata(
        'data3') == "" else postinfo.getdata('data3')

    if acc_post_datas:

        neighborhood = acc_post_datas[2] if len(
            acc_post_datas) > 2 else neighborhood
    city.send_keys(neighborhood)

    # zip code setup

    try:
        postal_code = b.driver.execute_script("""return document.evaluate('//*[@id="postal_code"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
        
        postcode = b.proxy_zip if postinfo.getdata(
            'data2') == "" else postinfo.getdata('data2')
        postal_code.send_keys(postcode)
    except:
        pass

    # time.sleep(random.choice([0.1, 0.3, 0.2, 0.4, 0.5]))

    # post body setup
    b_body = b.driver.execute_script("""return document.evaluate('//*[@id="PostingBody"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    # b.scroll_like_user(b_body)
    postbody = ps_str(postinfo.getdata('data4'))
    print('body text typing')
    b_body.send_keys(postbody.with_email(body_mail))
    print('price text typing done')

    # price setup
    b_price = b.driver.execute_script("""return document.evaluate('//*[@name="price"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    # b.scroll_like_user(b_price)
    price = postinfo.price if postinfo.getdata(
        'data11') == "" else postinfo.getdata('data11')
    b_price.send_keys(price)
    print('data11 price set {0}'.format(price))
    # sqft setup
    sqft = b.driver.execute_script("""return document.evaluate('//*[@name="surface_area"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    sqft.clear()
    # b.scroll_like_user(b_price)
    type = [1000, 900, 800, 600]
    one_type = random.choice(type)
    sizein_sqft = one_type if postinfo.getdata(
        'data12') == "" else postinfo.getdata('data12')
    sqft.send_keys(sizein_sqft)
    print('data12 size in sqft set {0}'.format(sizein_sqft))

    # housing type setup
    # time.sleep(1000)
    try:
        type = [1, 4, 5, 6]
        one_type = random.choice(type)
        one_type = one_type if postinfo.getdata('data6') == "" else postinfo.getdata('data6')

        append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(one_type))
        ju = str('$("#ui-id-2"){}'.format(append))

        b.script_run('$("#ui-id-2").empty();', message='housing_type empty')
        b.script_run(ju, message='housing_type append')
        print('data6 housing type setup set {0}'.format(one_type))

    except Exception as e:
        print('housing_type error', e)

    # laundry setup
    try:
        laundry = 1
        laundry = laundry if postinfo.getdata(
            'data7') == "" else postinfo.getdata('data7')
        append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(laundry))
        ju = str('$("#ui-id-3"){}'.format(append))

        b.script_run('$("#ui-id-3").empty();', message='laundry empty')
        b.script_run(ju, message='laundry append')
        print('data6 laundry append set {0}'.format(laundry))
    except Exception as e:
        print('laundry error', e)

    # parking setup
    try:
        parking = [1, 2]

        parking = random.choice(parking)
        parking = parking if postinfo.getdata(
            'data8') == "" else postinfo.getdata('data8')

        append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(parking))
        ju = str('$("#ui-id-4"){}'.format(append))

        b.script_run('$("#ui-id-4").empty();', message='parking empty')
        b.script_run(ju, message='parking append')
        print('data8 parking empty set {0}'.format(parking))
    except Exception as e:
        print('parking error', e)

    # bedrooms setup
    try:
        bedrooms = postinfo.bed if postinfo.getdata(
            'data9') == "" else postinfo.getdata('data9')

        append = '.append("<option value=\'{}\' selected>any</option>");'.format(
            str(bedrooms))
        ju = str('$("#ui-id-5"){}'.format(append))

        b.script_run('$("#ui-id-5").empty();', message='bedrooms empty')
        b.script_run(ju, message='bedrooms append')
        print('data9 bedrooms set {0}'.format(bedrooms))
    except Exception as e:
        print('bedrooms error', e)

    # bathrooms setup
    try:
        bathrooms = postinfo.bat if postinfo.getdata(
            'data10') == "" else postinfo.getdata('data10')
        append = '.append("<option value=\'{}\' selected>any</option>");'.format(
            str(bathrooms))
        ju = str('$("#ui-id-6"){}'.format(append))

        b.script_run('$("#ui-id-6").empty();', message='bathrooms empty')
        b.script_run(ju, message='bathrooms append')
        print('data10` bathrooms set {0}'.format(bathrooms))
    except Exception as e:
        print('bathrooms error', e)
    # rent period setup
    try:

        append = '.append("<option value=\'3\' selected>any</option>");'
        ju = str('$("#ui-id-1"){}'.format(append))

        b.script_run('$("#ui-id-1").empty();', message='rent period empty')
        b.script_run(ju, message='rent period append')
        print('data10` period set {0}'.format(append))
    except Exception as e:
        print('rent period error', e)
    try:

        append = '.append("<option value=\'3\' selected>any</option>");'
        ju = str('$("#ui-id-1"){}'.format(append))

        b.script_run('$("#rent_period").empty();', message='rent period empty')
        b.script_run(ju, message='rent period append')
        print('data10` period set {0}'.format(append))
    except Exception as e:
        print('rent period error', e)

    # show address click
    street = False if postinfo.getdata(
        'data13') == "" else postinfo.getdata('data13')
    if street:
        show_address_ok = b.select_element_xpath(
            '//*[@name="show_address_ok"]', 'show address click')
        show_address_ok.click()
        b_street = b.select_element_xpath(
            '//*[@name="xstreet0"]', 'street')
        b_street.send_keys(street)

    # email setup
    nextpage = b.driver.execute_script("""return document.evaluate('//*[@name="go"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")

    nextpage.click()
    
    # no pass click
    # time.sleep(120)
    print(b.current_url())
    if 's=rentcheck' in b.current_url():

        rentcheck = b.select_element_xpath('//*[@id="new-edit"]/div/div[2]/button')
        rentcheck.click()
    nextpage = b.driver.execute_script("""return document.evaluate('//*[contains(text(),"continue")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    # b.scroll_like_user(nextpage)

    nextpage.click()
    if 's=geoverify' in b.current_url():
        area_change_ok= b.driver.execute_script("""return document.evaluate('//*[@name="area_change_ok"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
        area_change_ok.click()

    classic_image= b.driver.execute_script("""return document.evaluate('//a[@id="classic"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    classic_image.click()
    plupload= b.driver.execute_script("""return document.evaluate('//input[@name="file"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    b.upload_multiple(plupload, account_id)
    doneWithImages= b.driver.execute_script("""return document.evaluate('//*[contains(text(),"done with images")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    doneWithImages.click()
    publish= b.driver.execute_script("""return document.evaluate('//*[@id="publish_top"]/button', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    publish.click()

    if 'pass?userid=' in b.current_url():
        input('pass?userid')
    # check tams page
    if 's=tou' in b.current_url():
        input('tams page')

    if 's=pn' in b.current_url():
        input('need pva')
    postdone=b.driver.execute_script("""return document.evaluate('//*[contains(text(),"View your post at")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;""")
    if postdone:
        # b.scroll_like_user(check_post)
        worker_acc.post_done(account_id, postdone.text)
        worker_acc.post_log(account_id, b.textProxy())

    print('post done')
    print('browser close')
    b.ipinfo_save(software_name='housing')

    b.exit()
    

    print('start :', starttime)
    print('end :', datetime.now().strftime("%H:%M:%S"))


setup = table()
setup.token_verify()
setup.pop_verify()

#w = int(input('how much worker you need? '))
# packages_id = input('proxy info by a line : ')
packages_id = '317345'

# worker = w + 1
worker = 2
# ........................start worker....................
open('active.txt', "w+")
utility = helper()
headers = {}
profile_ids = {}
acc = accounts()
post = post()
# if sys.platform not in ['Windows', 'win32', 'cygwin']:
#     display = Display(visible=0, size=(1024, 768))
#     display.start()
# x = threading.Thread(target=smtp.reply_check, args=(1,), daemon=True)
# x.start()
while True:
    # utility.network_check()
    if setup.token_off():
        print('software off now but reply checking runing')
        time.sleep(10)
        continue
    one_account = acc.get_account()
    print(one_account)
    if one_account == None:
        print('account not find for worker')
        time.sleep(10)
        continue
    postinfo = post.get_post(one_account['id'])
    body_mail = None
    if postinfo == None:

        print('post not find for worker')
        time.sleep(10)
        continue
    print('account last use time is : ', one_account['last_updates'])

    # if path.isdir('profiles/' + str(one_account['id'])) == True:
        # shutil.rmtree('profiles/' + str(one_account['id']))

    print('main')
    main(one_account, post, packages_id, body_mail)
    time.sleep(10)
