import urllib.request
import random
username = 'forsoft'
password = 'forsoft'
state = 'us_california'
entry = ('http://customer-%s-st-%s-sessid-%s:%s@pr.oxylabs.io:7777' %
         (username, state, '21asws', password))
query = urllib.request.ProxyHandler({
    'http': entry,
    'https': entry,
})
print(entry)
user = 'customer-{user}-st-{country}_{st}-sessid-{session}'.format(
    user='user', country='US'.lower(), st='california', session='okssss')
print(user)
execute = urllib.request.build_opener(query)
print(execute.open('http://ip-api.com/json').read())
