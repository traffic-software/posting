import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
import sys
from selenium.webdriver.support.ui import WebDriverWait
import time
import os
import random
from selenium.webdriver.common.action_chains import ActionChains
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
driver = uc.Chrome(
            driver_executable_path='chromedriver.exe', use_subprocess=True)
time.sleep(2)
login = 'https://accounts.google.com/signin/v2/identifier?continue=https%3A%2F%2Fmyaccount.google.com%2Fsigninoptions%2Frescuephone&osid=1&rart=ANgoxcfbj5MICImsby3i6E4WliB4NiCObSuRKGTYLSt03bQVr5EN0ekxnuxLrRGkyz5DKW13ZqMxZkUoZn1oMKAXz3u6m-8mXw&service=accountsettings&flowName=GlifWebSignIn&flowEntry=ServiceLogin'

driver.get(login)

def visibil_element(by, selector, wait=5):
        
        element = False
        if by == 'name':
            byselector = By.NAME
        if by == 'xpath':
            byselector = By.XPATH
        if by == 'css':
            byselector = By.CSS_SELECTOR
        if by == 'id':
            byselector = By.ID
        try:

            element = WebDriverWait(driver, wait).until(
                EC.visibility_of_element_located((byselector, selector)))

        except Exception as e:
            print(e)
            element = False
        if element == False:
            
            print("visibil_element not find: ", selector)
        else:
            print(selector)
        return element

def firstLine():
    # list to store file lines
    lines = []
    # read file
    with open(r"input.txt", 'r') as fp:
        # read an store all lines into list
        lines = fp.readlines()

    # Write file
    with open(r"input.txt", 'w') as fp:
        for number, line in enumerate(lines):
            if number != 0:
                fp.write(line)
    mailinfo = lines[0].split(':')
    return mailinfo
    
def apandLine(listinfo, filename="output.txt"):
    inputfile = open(r'{0}'.format(filename), 'a')
    line = ':'.join(listinfo)
    inputfile.write(f'{line}')
    inputfile.close()

def ran_password():
        characters ="abcdefghijklmnopshwyz"
        upper ="ABCDEFGHIJKLMNOPQPSHWYZ"
        symbol ="@%"
        num = "0123456789"
        string = characters+symbol+num+upper
        length = 8
        password = "".join(random.sample(string,length))
        print("Random password:",password)
        return password

mailinfo= firstLine()

print(mailinfo)
email_address = mailinfo[0]
email_pass_1 = mailinfo[1].replace('\\n','')
email_pass = email_pass_1.replace('\\t','')

recovery_email= mailinfo[2].replace('\\n','')
recovery_email_2= recovery_email.replace('\\n','')
recovery_email= recovery_email_2.replace('\\t','')
new_pass = ran_password()

send_keys = True

### Gmail login Start
time.sleep(5)
input_email = visibil_element('css', 'input',5)
input_email.send_keys(email_address)
time.sleep(3)
input_email.send_keys(Keys.RETURN)
gmail_error = visibil_element('xpath', '//div[@class="o6cuMc"]',3)
if gmail_error:
    driver.close()
    # exit()

input_pass =visibil_element('xpath', '//input[@type="password"]',3)
input_pass.send_keys(email_pass)
input_pass.send_keys(Keys.RETURN)
time.sleep(3)

### gmail login  end

remove_number = visibil_element('xpath', '(//span[@class="DPvwYc MRcnif"])[2]',2)
input_pass_1 = visibil_element('xpath', '(//input[@type="password"])[1]',2)
if input_pass_1  == remove_number:
    my_acc_link=None
    driver.close()
    # exit()

recovery_link = "https://myaccount.google.com/recovery/email"
device_check = "https://myaccount.google.com/u/0/device-activity"
pass_change = "https://myaccount.google.com/signinoptions/password"
my_acc_link = driver.current_url.split('?')[1]

### Pass change
try:
    input_pass_1 = visibil_element('xpath', '(//input[@type="password"])[1]',3)
    if input_pass_1:
        input_pass_1.send_keys(new_pass)
    input_pass_2 = visibil_element('xpath',  '(//input[@type="password"])[2]',3)
    if input_pass_2:
        input_pass_2.send_keys(new_pass)
    pass_submit = visibil_element('xpath','//button[@type="submit"]',3)
    if pass_submit:
        pass_submit.click()
    else:
        
        pass_submit = visibil_element('xpath', '//button[@type="button"]',3)
        if pass_submit:
            pass_submit.click()
except NoSuchElementException:
    pass

try:
    remove_number = visibil_element('xpath', '(//span[@class="DPvwYc MRcnif"])[2]',3)
    if remove_number:
        remove_number.click()
    
    remove_number_f = visibil_element('xpath','(//span[@class="CwaK9"]//child::span[@class="RveJvd snByac"])[4]',3)
    if remove_number_f:
        remove_number_f.click()
except NoSuchElementException:
    pass

my_acc_link = driver.current_url.split('?')[1]

### check Device
try:
    device_check_link = f'{device_check}?{my_acc_link}'
    driver.get(device_check_link)
    time.sleep(2)
    check_device_count = len(driver.find_elements(By.XPATH, '//div[@class="Ivdcjd"]'))
    check_device_count_f = check_device_count - 1
    for x in range(0,check_device_count_f):
        device_log_out_format_value = 2
        time.sleep(2)
        device_log_out = visibil_element('xpath','(//div[@class="Ivdcjd"])[{0}]'.format(device_log_out_format_value),5)
        if device_log_out:
            device_log_out.click()
        device_log_out_format_value += 1
        try:
            device_log_out_f = visibil_element('xpath','//span[text()="Sign out"]//parent::button[@type="button"]',3)
            if device_log_out_f:
                device_log_out_f.click()
        except NoSuchElementException:
            device_log_out_f = visibil_element('xpath','(//button[@type="button"])[3]',3)
            if device_log_out_f:
                device_log_out_f.click()
        device_log_out_f =visibil_element('xpath', '(//span[@class="VfPpkd-vQzf8d"])[4]',3)
        if device_log_out_f:
            device_log_out_f.click()
        try:
            okk_click =visibil_element('xpath','(//button[@jsname="LgbsSe"]//child::span)[2]',3)
            if okk_click:
                okk_click.click()
        except NoSuchElementException:
            pass
        time.sleep(3)
except NoSuchElementException:
    pass

my_acc_link = driver.current_url.split('?')[1]

### Pass change
try:
    pass_change_link = f'{pass_change}?{my_acc_link}'
    driver.get(pass_change_link)
    time.sleep(2)
    input_pass_1 = driver.find_element(By.XPATH, '(//input[@type="password"])[1]').send_keys(new_pass)
    input_pass_2 = driver.find_element(By.XPATH, '(//input[@type="password"])[2]').send_keys(new_pass)
    time.sleep(1)
    pass_submit = driver.find_element(By.XPATH, '//button[@type="submit"]').click()
    time.sleep(2)
    print("Gmail Password: ",new_pass)
except NoSuchElementException:
    pass

### Gmail name
try:
    gmail_link_for_mail = 'https://myaccount.google.com/personal-info'
    driver.get(gmail_link_for_mail)
    time.sleep(3)
    new_gmail = driver.find_element(By.XPATH, '(//div[@class="bJCr1d"])[4]').text
except NoSuchElementException:
    pass

mailinfo[0]=new_gmail
mailinfo[1]=new_pass
apandLine(mailinfo)

### Recovery
try:
    recovery_link_f = f'{recovery_link}?{my_acc_link}'
    driver.get(recovery_link_f)
    time.sleep(2)
    input_recovery_clear = driver.find_element(By.XPATH, '(//input[@type="text"])[2]').clear()
    time.sleep(1)
    input_recovery = visibil_element('xpath', '(//input[@type="text"])[2]',3)
    input_recovery.send_keys(recovery_email)
    
    rec_submit = visibil_element('xpath', '//button[@type="submit"]',3)
    
    # if rec_submit:
    #     rec_submit.click()

    rec_submit = visibil_element('xpath', '//button[@type="submit"]',3)
    driver.execute_script("arguments[0].click();", rec_submit)

    time.sleep(2)
    driver.close()
except:
    driver.close()



