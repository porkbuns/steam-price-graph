#!/usr/bin/env python

import math
import datetime
import time
import os

from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

from templates import helpers
from mako.lookup import TemplateLookup
import GChartWrapper
import models
import SteamApi
import webapp2


class RenderMako(object):
  def __init__(self, *args, **kwargs):
    self._lookup = TemplateLookup(*args, **kwargs)

  def __getattr__(self, template_name):
    template_name = '%s.mako.html' % template_name
    return self._lookup.get_template(template_name)


class BaseHandler(webapp2.RequestHandler):
    '''
    Yet another request handler wrapper to add the right dash of
    functionality. Sigh.
    '''
    renderer_ = RenderMako(directories=['templates'], format_exceptions=True)

    def render(self, basename):
      values = {'h': helpers, 'c': self}
      self.response.out.write(
        getattr(BaseHandler.renderer_, basename).render_unicode(**values))


class IndexHandler(BaseHandler):
    PAGE_SIZE = 20

    def head(self, *args, **kwargs):
      self.get(*args, **kwargs)

    def get(self):
        self.page = int(self.request.get('page', 1))
        cursor = self.request.get('cursor', None)
        self.query = self.request.get('q', None)

        if self.query:
          self.games = models.SteamGame.search(self.query)
        else:
          self.games_query = models.SteamGame.all().order(
            '-price_last_changed')

          offset = 0
          if cursor:
            self.games_query.with_cursor(cursor)
          else:
            offset = (self.page - 1) * IndexHandler.PAGE_SIZE
          self.games = self.games_query.fetch(IndexHandler.PAGE_SIZE, offset=offset)

        self.render('index')


class GameHandler(BaseHandler):
    def head(self, *args, **kwargs):
      self.get(*args, **kwargs)

    def get(self, steam_id):
        self.game_model = models.SteamGame.get_by_key_name(
          models.SteamGame.get_key_name(steam_id))
        if not self.game_model:
            self.abort(404)  # could not find game
        self.game = self.game_model.to_steam_api()

        self.render('game')

class SparklineHandler(BaseHandler):
    DEFAULT_NUMBER_OF_DAYS = 29
    DEFAULT_WIDTH = 60
    DEFAULT_HEIGHT = 18

    def get(self, steam_id):
        chart_type = self.request.get('type', 'ls')
        chart_width = int(self.request.get(
            'width', SparklineHandler.DEFAULT_WIDTH))
        chart_height = int(self.request.get(
            'height', SparklineHandler.DEFAULT_HEIGHT))
        chart_days = int(self.request.get(
            'days', SparklineHandler.DEFAULT_NUMBER_OF_DAYS))

        self.game_model = models.SteamGame.get_by_key_name(models.SteamGame.get_key_name(steam_id))
        if not self.game_model:
            self.abort(404)  # could not find game

        url = helpers.sparkline_url(self.game_model, chart_type=chart_type,
                                    width=chart_width, height=chart_height,
                                    days=chart_days)
        self.redirect(url)


class WebHookHandler(webapp2.RequestHandler):
    def get(self, action):
        self.process(action)

    def post(self, action):
        self.process(action)

    def process(self, action):
        if action == 'queue_update':
            self.queue_update()
        elif action == 'update':
            self.update()
        elif action == 'update_page':
            self.update_page(int(self.request.get('page')))
        else:
            self.abort(404)

    def queue_update(self):
        taskqueue.add(queue_name='updater-queue',
                      url='/webhooks/update',
                      method='GET',
                      target='webhook-backend')

    def update(self):
        number_of_pages = SteamApi.get_number_of_pages()
        for page in xrange(1, number_of_pages + 1):
            taskqueue.add(queue_name='updater-queue',
                          url='/webhooks/update_page?page=%d' % page,
                          method='GET',
                          target='webhook-backend')
            self.response.out.write('...page %d<br>' % page)
        self.response.out.write('Enqueued %d pages' % number_of_pages)

    def update_page(self, page):
        games = SteamApi.get_games(page)
        game_models = models.SteamGame.get_by_key_name(
          [models.SteamGame.get_key_name(g.id) for g in games])
        to_write = []
        to_index = []
        for game, game_model in zip(games, game_models):
            self.response.out.write('Starting: %s...' % game.name)
            game_key_name = models.SteamGame.get_key_name(game.id)

            should_reindex = False
            if not game_model:
                game_model = models.SteamGame(key_name=game_key_name)
                should_reindex = True
            else:
                should_reindex = game_model.name != game.name

            game_model.steam_id = game.id
            game_model.name = game.name
            game_model.current_price = game.price
            to_write.append(game_model)

            # Only reindex if the entry is new, or the name has changed.
            if should_reindex:
                to_index.append(game_model)

            self.response.out.write('done -- ')
            self.response.out.write('%r' % game_model.price_change_list)
            self.response.out.write(' to_index=%r' % should_reindex)
            self.response.out.write('<br>')
        self.response.out.write('Writing...')
        db.put(to_write)
        for game_model in to_index:
          game_model.index()
        self.response.out.write('done<br>')
        self.response.out.write('<br>Done.')
        self.response.out.write('<br><a href="?page=%d">Next</a>' % (page + 1))


app = webapp2.WSGIApplication(
    [('/', IndexHandler),
     webapp2.Route('/games/<steam_id>/sparkline', SparklineHandler),
     webapp2.Route('/games/<steam_id>', GameHandler),
     webapp2.Route('/webhooks/<action>', WebHookHandler)],
    debug=True)
