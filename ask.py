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
from weakref import proxy
from pyvirtualdisplay import Display
from datetime import datetime
import smtp
from ps_lib.browser import browser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.ps_str import ps_str
from ps_lib.imap import imap
from selenium.webdriver.common.keys import Keys
import os
import pyautogui
import re

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
bundle_dir = path.abspath(path.dirname(__file__))


def main(account_data, postinfo, packages_id, body_mail):
    # work start time
    starttime = datetime.now().strftime("%H:%M:%S")

    print(datetime.now().strftime("%H:%M:%S"))

    account_id = account_data['id']
    print("account id: ", account_id)
    worker_acc = accounts()
    settings = table()
    worker_token = worker_acc.get_token(account_data)
    worker_keyword = worker_acc.get_ask_keyword(account_data, worker_token)

    b = browser(account_id, pva=account_data)
    time.sleep(5)
    # if b.PROXY_PASS == False:
    #     b.exit()
    #     print('proxy condition not fulfilled')
    #     # worker_acc.ban_3(account_id, 5)
    #     time.sleep(10)
    #     return False

    try:

        b.get_url('https://www.google.com/search?q={q}'.format(
            q=worker_keyword['keyword'].replace(' ', '+')))
    except:
        b.exit()
    # time.sleep(240)
    # q = b.select_element_xpath(
    #     '//*[@name="q"]', 'q')
    # q.send_keys(character)

    try:
        center_col = b.select_element_xpath(
            '//*[@id="center_col"]', 'center_col')
    except:
        b.exit()
        exit()
    # loing tail keyowrd

    arg = b.element_xpath(center_col, '//*[@id="botstuff"]', 'botstuff')
    keywords = arg.find_elements_by_tag_name("a")
    related_keywords = []
    for item in keywords:
        related_keywords.append(item.text)

    # RELATED_QUESTION

    get_new_faqs = b.elements_xpath(
        center_col, '//*[starts-with(@id,"RELATED_QUESTION_LINK")]', 'faqs')
    for item in get_new_faqs:
        try:
            item.click()
            # print(i.get_attribute('innerHTML'))
            time.sleep(2)

        except:
            print("Element is not clickable")
    get_new_faqs2 = b.elements_xpath(
        center_col, '//*[starts-with(@id,"RELATED_QUESTION_LINK")]', 'faqs2')
    count = len(get_new_faqs2)
    for item in reversed(list(get_new_faqs2)):
        try:
            count = count-1
            if (len(get_new_faqs)+1) > count:
                break
            item.click()
            time.sleep(2)
            # print(i.get_attribute('innerHTML'))

        except:
            print("Element is not clickable")
    get_new_faqs3 = b.elements_xpath(
        center_col, '//*[starts-with(@id,"RELATED_QUESTION_LINK")]', 'faqs3')
    count = len(get_new_faqs3)
    for item in reversed(list(get_new_faqs3)):
        try:
            count = count-1
            if (len(get_new_faqs2)+5) > count:
                break
            item.click()
            time.sleep(2)
            # print(i.get_attribute('innerHTML'))

        except:
            print("Element is not clickable")

    time.sleep(5)
    faqs = b.elements_xpath(
        center_col, '//*[starts-with(@id,"RELATED_QUESTION_LINK")]', 'faqs4')
    len(faqs)
    related_question = []

    for item in faqs:

        # print(item.get_attribute('innerHTML'))

        # description
        try:
            description = item.find_element_by_css_selector(
                '[data-attrid="wa:/description"]')
            description = description.get_attribute('innerHTML')
        except:
            description = 'no description'

        # link = b.element_xpath(
        #     item, '//*[starts-with(@href,"http")]', 'link')
        try:
            link = item.find_element_by_css_selector(
                'a:not([href*="google.com/search"])')
            link = link.get_attribute('href')
        except:
            link = 'no link'
        try:
            faq = item.find_element_by_css_selector('div[id^="exacc_"]')
            faq = faq.text
        except:
            faq = 'not faq'

        question = {
            'ans': re.sub('<[^<]+?>', '', description),
            'link': link,
            'question': re.sub('<[^<]+?>', '', faq)
        }

        related_question.append(question)

    # print('related_question')
    # print(related_question)
    # print("related_keywords")
    # print(related_keywords)
    worker_acc.save_data(account_data, worker_token, {"parent_id": worker_keyword['id'],
                         "keywords": related_keywords, "question": related_question})
    exit()

    # https://post.craigslist.org/k/sib7px0t7BGflPX08yY-RA/Qdjqi?s=subarea
    if 'subarea' in b.current_url():
        sub_aria = b.select_elements('input[type=radio]')

        sub_aria = random.choice(sub_aria)
        # b.scroll_like_user(sub_aria)

        sub_aria.click()
    if 's=hood' in b.current_url():
        sub_aria = b.select_elements('input[type=radio]')
        sub_aria = random.choice(sub_aria)
        # b.scroll_like_user(sub_aria)

        sub_aria.click()
    button = b.select_element_xpath(
        '/html/body/article/section/form/ul/li[4]', 'click on housing offered')
    # b.scroll_like_user(button)
    button.click()
    button = b.select_element_xpath(
        '//*[@id="new-edit"]/div/label/label[2]/div/span[1]', 'click on apartments / housing for rent')
    # b.scroll_like_user(button)
    button.click()

    # Posting Title setup
    b_sub = b.select_element_xpath('//*[@id="PostingTitle"]', 'PostingTitle')
    # b.scroll_like_user(b_sub)

    postsub = ps_str(postinfo.getdata('data1'))
    print('b_sub text typing')
    for character in postsub.Spin():
        b_sub.send_keys(character)
        # time.sleep(random.choice([0.1, 0.3, 0.2, 0.4, 0.5]))
    print('b_sub text typing done')
    # b_sub.send_keys(character)
    # city or neighborhood setup
    city = b.select_element_xpath(
        '//*[@id="geographic_area"]', 'postal code"]')
    # b.scroll_like_user(postal_code)
    neighborhood = b.proxy_city if postinfo.getdata(
        'data3') == "" else postinfo.getdata('data3')
    city.send_keys(neighborhood)
    # zip code setup
    postal_code = b.select_element_xpath(
        '//*[@id="postal_code"]', 'postal code"]')
    # b.scroll_like_user(postal_code)
    postcode = b.proxy_zip if postinfo.getdata(
        'data2') == "" else postinfo.getdata('data2')
    postal_code.send_keys(postcode)
    # time.sleep(random.choice([0.1, 0.3, 0.2, 0.4, 0.5]))

    # post body setup
    b_body = b.select_element_xpath('//*[@id="PostingBody"]', 'PostingBody')
    # b.scroll_like_user(b_body)
    postbody = ps_str(postinfo.getdata('data4'))
    print('body text typing')
    b_body.send_keys(postbody.with_email(body_mail))
    # for character in postbody.with_email(body_mail):

    #     b_body.send_keys(character)
    #     # time.sleep(random.choice([0.1, 0.2]))
    print('price text typing done')
    # b_body.send_keys(postbody.with_email(body_mail))

    # price setup
    b_price = b.select_element_xpath(
        '//*[@id="new-edit"]/div/fieldset[1]/div/div[1]/label[1]/label/input', 'price set')
    # b.scroll_like_user(b_price)
    price = postinfo.price if postinfo.getdata(
        'data11') == "" else postinfo.getdata('data11')
    b_price.send_keys(price)
    # sqft setup
    sqft = b.select_element_xpath(
        '//*[@name="surface_area"]', 'size in sqft set')
    sqft.clear()
    # b.scroll_like_user(b_price)
    type = [1000, 900, 800, 600]
    one_type = random.choice(type)
    sizein_sqft = one_type if postinfo.getdata(
        'data12') == "" else postinfo.getdata('data12')
    sqft.send_keys(sizein_sqft)

    # housing type setup
    try:
        type = [1, 4, 5, 6]
        one_type = random.choice(type)
        one_type = one_type if postinfo.getdata(
            'data6') == "" else postinfo.getdata('data6')

        append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(one_type))
        ju = str('$("#ui-id-1"){}'.format(append))

        b.script_run('$("#ui-id-1").empty();', message='housing_type empty')
        b.script_run(ju, message='housing_type append')

    except Exception as e:
        print('housing_type error', e)

    # laundry setup
    try:
        laundry = 1
        laundry = laundry if postinfo.getdata(
            'data6') == "" else postinfo.getdata('data6')
        append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(laundry))
        ju = str('$("#ui-id-2"){}'.format(append))

        b.script_run('$("#ui-id-2").empty();', message='laundry empty')
        b.script_run(ju, message='laundry append')
        # b.select_dropdown('#ui-id-2',1)
    except Exception as e:
        print('laundry error', e)

    # parking setup
    try:
        parking = [1, 2]

        parking = random.choice(parking)
        parking = parking if postinfo.getdata(
            'data8') == "" else postinfo.getdata('data8')

        append = '.append("<option value=\'{}\' selected>any</option>");'.format(str(parking))
        ju = str('$("#ui-id-3"){}'.format(append))

        b.script_run('$("#ui-id-3").empty();', message='parking empty')
        b.script_run(ju, message='parking append')
    except Exception as e:
        print('parking error', e)

    # bedrooms setup
    try:
        bedrooms = postinfo.bed if postinfo.getdata(
            'data9') == "" else postinfo.getdata('data9')

        append = '.append("<option value=\'{}\' selected>any</option>");'.format(
            str(bedrooms))
        ju = str('$("#ui-id-4"){}'.format(append))

        b.script_run('$("#ui-id-4").empty();', message='bedrooms empty')
        b.script_run(ju, message='bedrooms append')
    except Exception as e:
        print('bedrooms error', e)

    # bathrooms setup
    try:
        bathrooms = postinfo.bat if postinfo.getdata(
            'data10') == "" else postinfo.getdata('data10')
        append = '.append("<option value=\'{}\' selected>any</option>");'.format(
            str(bathrooms))
        ju = str('$("#ui-id-5"){}'.format(append))

        b.script_run('$("#ui-id-5").empty();', message='bathrooms empty')
        b.script_run(ju, message='bathrooms append')
    except Exception as e:
        print('bathrooms error', e)
    # rent period setup
    try:

        append = '.append("<option value=\'3\' selected>any</option>");'
        ju = str('$("#ui-id-6"){}'.format(append))

        b.script_run('$("#ui-id-6").empty();', message='rent period empty')
        b.script_run(ju, message='rent period append')
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
    b_email = b.select_element_xpath('//*[@name="FromEMail"]', 'select email')
    # b.scroll_like_user(b_email)

    b_email.send_keys(account_data['email'])
    nextpage = b.select_element_xpath('//*[@name="go"]', 'go next page')
    # b.scroll_like_user(nextpage)
    nextpage.click()
    # no pass click
    if 's=geoverify=' in b.current_url():

        sub_aria = b.select_element_xpath('//*[@name="area_change_ok"]')
        sub_aria.click()
    nextpage = b.select_element_xpath(
        '//*[@id="leafletForm"]/button', 'go from map page')
    # b.scroll_like_user(nextpage)

    nextpage.click()
    if 's=geoverify=' in b.current_url():

        sub_aria = b.select_element_xpath('//*[@name="area_change_ok"]')
        sub_aria.click()

     # image upload prosess start
    image1 = b.select_element_xpath(
        '//*[@id="plupload"]', 'image option 1')
    # b.scroll_like_user(nextpage)

    # image upload prosess end
    time_sleep = b.upload_multiple(image1, account_id)
    time.sleep(time_sleep)
    nextpage = b.select_element_xpath(
        '/html/body/article/section/form/button', 'go from image page')
    # b.scroll_like_user(nextpage)
    nextpage.click()
    nextpage = b.select_element_xpath(
        '//*[@id="publish_top"]/button', 'go from publish page')
    # b.scroll_like_user(nextpage)
    nextpage.click()
    time.sleep(10)

    if not pp:
        pop = popacc.split(":")
        popmail = imap(account_id, pop[0], pop[1])
    else:
        popmail = imap(
            account_id, account_data['email'], account_data['password'])

    counter = 0
    postdone = False

    while True:
        time.sleep(10)
        if postdone == True:
            break
            postdone = False

        counter = counter+1

        popmail.messages()
        links = popmail.get_link(
            ['craigslist.org/pass', 'craigslist.org/login/onetime'])

        print('Get links')

        for link in links:

            conf_link = 'window.location.href = "{};'.format(link)
            b.script_run(conf_link, 'link click to verify')

            postdone = True
            break

        if counter > 6:
            worker_acc.post_error(account_id, 'verify link not recived')
            worker_acc.ban_3(account_id, status=2)
            print("link not recived")
            break

    if 'pass?userid=' in b.current_url():
        # no pass click
        nextpage = b.select_element_xpath(
            '/html/body/section/section/div[2]/div[1]/form/div/input', 'no pass click')
        # b.scroll_like_user(nextpage)
        nextpage.click()
    # check tams page
    if 's=tou' in b.current_url():

        nextpage = b.select_element_xpath(
            '//*[@id="new-edit"]/div/div[4]/div[1]/button', 'tams')
        # b.scroll_like_user(nextpage)
        nextpage.click()

    if 's=pn' in b.current_url():

        pva_verify = settings.pva_verify()
        if "yes" == pva_verify:
            pva = b.select_element_xpath(
                '//*[@id="new-edit"]/div/div[3]/div[1]/label/label/input', 'number for pva')

            pva_number = str(input("please enter number for pva : "))
            pva.send_keys(pva_number)
            pva_num_submit = b.select_element_xpath(
                '//*[@id="new-edit"]/div/div[3]/div[2]/button', 'pva code')
            # b.scroll_like_user(pva_num_submit)
            pva_num_submit.click()
            pva_code = str(input("please enter code for pva : "))
            pvacode = b.select_element_xpath(
                '//*[@id="userCode"]', 'number for pva')
            # b.scroll_like_user(pvacode)
            pvacode.send_keys(pva_code)
            pva_code_submit = b.select_element_xpath(
                '//*[@id="new-edit"]/div/div[2]/div[5]/button', 'pva code submit')
            # b.scroll_like_user(pva_code_submit)
            pva_code_submit.click()
            time.sleep(30)

        else:
            worker_acc.post_error(account_id, "no pva")
            worker_acc.ban_3(account_id, status=3)

    if b.try_xpath("//*[contains(text(),'View your post at')]"):
        check_post = b.select_element_xpath(
            "//*[contains(text(),'View your post at')]", 'post link check')
        # b.scroll_like_user(check_post)
        worker_acc.post_done(account_id, check_post.text)
        worker_acc.post_log(account_id, b.textProxy())

    print('post done')
    print('browser close')
    b.ipinfo_save(software_name='housing')

    b.exit()
    popmail.close()

    print('start :', starttime)
    print('end :', datetime.now().strftime("%H:%M:%S"))


setup = table()
setup.token_verify()
setup.pop_verify()

# w = int(input('how much worker you need? '))
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
if sys.platform not in ['Windows', 'win32', 'cygwin']:
    display = Display(visible=0, size=(1024, 768))
    display.start()
# x = threading.Thread(target=smtp.reply_check, args=(1,), daemon=True)
# x.start()
while True:
    # utility.network_check()
    if setup.token_off():
        print('software off now but reply checking runing')
        time.sleep(60)
        continue
    one_account = acc.get_account()
    if one_account == None:
        print('account not find for worker')
        time.sleep(60)
        continue
    postinfo = post.get_post(one_account['id'])
    body_mail = None
    if postinfo == None:

        print('post not find for worker')
        time.sleep(10)
        continue
    print('account last use time is : ', one_account['last_updates'])

    if path.isdir('profiles/' + str(one_account['id'])) == True:
        shutil.rmtree('profiles/' + str(one_account['id']))

    print('main')
    main(one_account, post, packages_id, body_mail)
    time.sleep(10)
