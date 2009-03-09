#!/usr/bin/env python
# Copyright (c) 2009 Manuel Aristarán <http://nerdpower.org>


import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template

import gviz_api
from datetime import datetime
from dateutil import parser as date_parser

import os

class TrackedValue(db.Model):
  timestamp = db.DateTimeProperty(auto_now_add=True)
  tracked_item = db.StringProperty(multiline=False)
  value = db.FloatProperty()

class MainHandler(webapp.RequestHandler):
  def get(self):

    query_template = "SELECT * from TrackedValue WHERE tracked_item = '%s' ORDER BY timestamp DESC LIMIT 1"

    template_values = {
      'USD': { 
        'compra': db.GqlQuery(query_template % 'USD-compra')[0],
        'venta': db.GqlQuery(query_template % 'USD-venta')[0]
      },
      'EUR': {
        'compra': db.GqlQuery(query_template % 'EUR-compra')[0],
        'venta': db.GqlQuery(query_template % 'EUR-venta')[0]
      },
      'HOST': self.request.environ['SERVER_NAME'] + (':' + self.request.environ['SERVER_PORT'] if self.request.environ['SERVER_PORT'] else '')
    }

    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, template_values))


class VizHandler(webapp.RequestHandler):
  def get(self):
    description = {"tracked_item": ("string", "Item"),
                   "value": ("number", "Cotizacion"),
                   "timestamp": ("datetime", "Fecha")}

    data_table = gviz_api.DataTable(description)

    data_table.LoadData(dict(zip(description.keys(), [getattr(i, k) for k in description.keys()]))  
                        for i in db.GqlQuery('SELECT * from TrackedValue %s' % ("WHERE tracked_item = '%s'" % self.request.get('ti') 
                                                                                if self.request.get('ti') else '')))

    resp = data_table.ToResponse(('timestamp', 'tracked_item', 'value'), 'timestamp', self.request.get('tqx'))
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
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
