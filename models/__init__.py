import datetime
import logging
import time
from google.appengine.ext import db

import SteamApi
from models.properties import JsonProperty
from search import Searchable


class SteamGame(Searchable, db.Model):
    '''
    Simple model that stores all that we care about for a given steam game.
    '''
    name = db.StringProperty()
    steam_id = db.StringProperty()
    price_change_list = JsonProperty(default=[])
    price_last_changed = db.DateTimeProperty()

    last_updated_on = db.DateTimeProperty(auto_now=True)
    created_on = db.DateTimeProperty(auto_now_add=True)

    INDEX_TITLE_FROM_PROP = 'name'
    INDEX_ONLY = [ 'name' ]
    INDEX_USES_MULTI_ENTITIES = False

    @property
    def last_updated_on_timestamp(self):
        return time.mktime(self.last_updated_on.timetuple())

    @property
    def created_on_timestamp(self):
        return time.mktime(self.created_on.timetuple())

    @property
    def price_last_changed_timestamp(self):
        return time.mktime(self.price_last_changed.timetuple())

    def get_current_price(self):
        if len(self.price_change_list):
            return self.price_change_list[0][1]
        elif hasattr(self, 'pickled_price_change_list_price') and \
                len(self.pickled_price_change_list_price) > 0:
            return SteamGame._float_to_price(self.pickled_price_change_list_price[0])
        else:
            return None

    def set_current_price(self, price):
        def has_price_change_list(price_change_list):
            return bool(len(price_change_list))

        def has_price_changed(new_price, current_price):
            if current_price is None and new_price is None:
                # Already know this has no price.
                return False
            elif (current_price is not None
                  and new_price is not None
                  and (abs(price - current_price) < 0.01)):
                # Price didn't change
                return False
            else:
                return True

        def should_update(new_price, current_price, price_change_list):
            if has_price_change_list(price_change_list):
                return has_price_changed(new_price, current_price)
            else: # Need to write first entry
                return True

        if not should_update(price, self.current_price, self.price_change_list):
            return

        price_change_list = []
        if len(self.price_change_list):
            price_change_list = self.price_change_list
        elif hasattr(self, 'pickled_price_change_list_price') and \
                len(self.pickled_price_change_list_price) > 0:
            price_change_list = zip(
                self.pickled_price_change_list_date,
                [SteamGame._float_to_price(p) for p
                 in self.pickled_price_change_list_price])

        now = long(time.time())
        # make a copy of the source. So that we don't mutate the default value
        # of the field. Augh.
        price_change_list = price_change_list[:]

        price_change_list.insert(
            0, [now, price])

        # Update the denormalized "most recent" values.
        self.price_change_list = price_change_list
        self.price_last_changed = datetime.datetime.fromtimestamp(
            price_change_list[0][0])

    current_price = property(get_current_price, set_current_price)

    def to_steam_api(self):
        return SteamApi.Game(
            id=self.steam_id, name=self.name, price=self.current_price)

    @staticmethod
    def get_key_name(game_id):
        return str(game_id)

    @staticmethod
    def _price_to_float(price):
        if price is None:
            return -1.0
        else:
            return price

    @staticmethod
    def _float_to_price(f):
        if f < 0:
            return None
        else:
            return f

