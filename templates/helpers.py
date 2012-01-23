import re
import datetime
import time

import GChartWrapper

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

def sparkline_url(game_model, chart_type='ls', width=60, height=18, days=29):
    game = game_model.to_steam_api()

    price_changes = game_model.price_change_list
    price_changes.append((0, None))

    i = 0
    now = long(time.time())
    values = []
    for unused_day in xrange(0, days):
        while now <= price_changes[i][0]:
            i += 1
        value = price_changes[i][1]
        if value is not None:
            value = int(value * 100)
        values.append(value)
        now -= (60 * 60 * 24)
    values.reverse()
    values.append(None)
    scale_max = 1
    if game_model.current_price is not None:
        scale_max = max(scale_max, int(game_model.current_price * 200))

    max_price = 1
    prices = [pair[1] for pair in game_model.price_change_list
              if pair[1] is not None]
    if prices:
        max_price = int(max(prices) * 100)
    scale_max = max(scale_max, max_price)

    graph = GChartWrapper.GChart(chart_type, values, encoding='text')
    if any(values):
        graph.scale(0, scale_max)
    graph.color('0077CC')
    graph.size(width, height)
    graph.marker('B', 'E6F2FA', 0, 0, 0)
    graph.marker('o', '003399', 0, len(values) - 2, 4)
    graph.fill('bg', 's', '00000000')
    graph.line(1,0,0)

    return graph.url
