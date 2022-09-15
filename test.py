
from datetime import date
d1 =str(date(2022,9,12))
d2 =str(date.today())

from datetime import datetime

def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y-%m-%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return abs((d2 - d1).days)
print(days_between(d1, d2))