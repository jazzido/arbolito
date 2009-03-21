#!/usr/bin/env python
# Copyright (c) 2009 Manuel Aristarán <http://nerdpower.org>

import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template

import gviz_api
from datetime import datetime
from dateutil import parser as date_parser
from string import join

import os, logging



def _mergeData(data):
  rv = []
  acc = {}
  prev_t = None
  for i in data:
    d = datetime(i.timestamp.year, i.timestamp.month, i.timestamp.day)
    if prev_t is not None and d != prev_t:
      rv.append(acc)
      acc = {}
    if acc.get('timestamp') is None:
      acc['timestamp'] = d
    acc[i.tracked_item] = i.value
    prev_t = d

  rv.append(acc)


  return rv


class TrackedValue(db.Model):
  timestamp = db.DateTimeProperty(auto_now_add=True)
  tracked_item = db.StringProperty(multiline=False)
  value = db.FloatProperty()

class MainHandler(webapp.RequestHandler):
  def get(self):

    query_template = "SELECT * from TrackedValue WHERE tracked_item = '%s' ORDER BY timestamp DESC LIMIT 1"

    today_rates = _mergeData(db.GqlQuery("SELECT * FROM TrackedValue WHERE tracked_item IN ('EUR-venta', 'EUR-compra', 'USD-venta', 'USD-compra') ORDER BY timestamp DESC LIMIT 4"))[0]

    template_values = {
      'USD': { 
        'compra': today_rates[u'USD-compra'],
        'venta': today_rates[u'USD-venta'],
      },
      'EUR': {
        'compra': today_rates[u'EUR-compra'],
        'venta': today_rates[u'EUR-venta']
      },
      'FECHA': today_rates[u'timestamp'],
      'HOST': self.request.environ['SERVER_NAME'] + (':' + self.request.environ['SERVER_PORT'] if self.request.environ['SERVER_PORT'] else '')
    }

    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))


class VizHandler(webapp.RequestHandler):

  data_table = None

  def get(self):
    
    data_table_description = {"timestamp": ("datetime", "Fecha")}

    columns = self.request.get('ti').split(',')
    for c in columns: data_table_description[c] = ("number", c)

    data_table = gviz_api.DataTable(data_table_description)

    data_table.LoadData(_mergeData(db.GqlQuery('SELECT * from TrackedValue %s ORDER BY timestamp' % ("WHERE tracked_item IN ('%s')" % 
                                                                                                     join(self.request.get('ti').split(','),
                                                                                                          "','")
                                                                                                     if self.request.get('ti') else ''))))
    resp = data_table.ToResponse(['timestamp'] + columns, (), self.request.get('tqx'))
    self.response.out.write(resp)
    

class TrackHandler(webapp.RequestHandler):
  def post(self):
    tracked_item = self.request.get('tracked_item')
    value = self.request.get('value')
    
    timestamp = self.request.get('timestamp')
    if timestamp is not None:
      try:
        timestamp = date_parser.parse(timestamp)
      except ValueError:
        response.out.write('Bad date format')
        self.error(401)
    else:
      timestamp = datetime.now()
    

    if tracked_item is None or value is None:
      response.out.write('Missing values')
      self.error(401)

    tv = TrackedValue()
    tv.tracked_item = tracked_item
    tv.value = float(value)
    tv.timestamp = timestamp

    tv.put()

    self.response.out.write('')


def main():
  application = webapp.WSGIApplication([('/', MainHandler),
                                        ('/track', TrackHandler),
                                        ('/vizdata', VizHandler)],
                                       debug=True)
  logging.getLogger().setLevel(logging.DEBUG)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
