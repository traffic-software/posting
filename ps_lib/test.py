
import requests
from email.policy import SMTP

import threading
import time
import shutil
import random
import string
import fnmatch
import sys
from os import path
from pyvirtualdisplay import Display
from datetime import datetime
from ps_lib.browser import browser
from ps_lib.uc import ucbrowser
from ps_lib.accounts import accounts
from ps_lib.psThread import psThread
from ps_lib.helper import helper
from ps_lib.ps_setup import table
from ps_lib.post import post
from ps_lib.captcha import capcha
from ps_lib.ps_str import ps_str
from ps_lib.imap import imap
import os

from selenium.webdriver.support.select import Select
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import re


token = 'eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjY0MzYwOTEsImlhdCI6MTYzNDkwMDA5MSwicmF5IjoiY2MzNzRmNTM3MTUyMDc3MWZjODAyNWM1MTM5OWIzYWUiLCJzdWIiOjIzMTAyOH0.OOd17iPERjvtNLc6KNa15nnG5hKXvkzeBf7aJa0ApMjWoO9on4NMC4UIbJRgJ8CtVk2dk7mVi5JwzC1e_zZXis-M2sx1GsFRgWum7BIlyxhYWYYp2rAJuW7YrcAn5MWBXC7E2DaKeeVonDgwzN1_FlUAEnS1iggGgdeKtTy3YZ75mH1z3lrsjjbml_vvP2PrCdpjEl7x2EXBizng3NNxqG72rF9OwI8I5mJj1ks0oHbdMNqOdScdExG6a9MJj9NXOFQmBx9C9bTgCCkhcd1T5bmX5-royaHq8LEyZnuE9HXMwo3mHL_Nny3mwCwftC95dMUqNARrQkY5p0hK4OUQfg'
country = 'russia'
operator = 'any'
product = 'amazon'

headers = {
    'Authorization': 'Bearer ' + token,
    'Accept': 'application/json',
}

response = requests.get('https://5sim.net/v1/user/buy/activation/' + country + '/' + operator + '/' + product, headers=headers)