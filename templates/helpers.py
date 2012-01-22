import re
import datetime
import time

def days_since(timestamp):
    diff = time.time() - timestamp;
    days_diff = int(diff / 60 / 60 / 24)

    if days_diff == 0:
        return 'today'
    elif days_diff == 1:
        return 'yesterday'
    else:
        return '%d days ago' % days_diff

def yyyymmdd(timestamp):
    date = datetime.datetime.fromtimestamp(timestamp)
    return date.strftime('%Y/%m/%d')

def price(price):
    if price is not None:
        if price == 0:
            return 'Free'
        else:
            return '$%.2f' % price
    else:
        return '-'
