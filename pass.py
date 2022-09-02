import random

def ran_password():
    characters ="abcde"
    symbol ="@%"
    num = "0123456789"
    string = characters+symbol+num
    length = 8
    password = "".join(random.sample(string,length))
    print(password)
ran_password()
