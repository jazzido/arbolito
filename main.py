#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template

import gviz_api
from datetime import datetime
from dateutil import parser as date_parser
from string import join

import os, logging

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

  data_table = None

  def get(self):
    
    data_table_description = {"timestamp": ("datetime", "Fecha")}

    columns = self.request.get('ti').split(',')
    for c in columns: data_table_description[c] = ("number", c)

    data_table = gviz_api.DataTable(data_table_description)

    data_table.LoadData([i for i in self._mergeData(db.GqlQuery('SELECT * from TrackedValue %s ORDER BY timestamp' % ("WHERE tracked_item IN ('%s')" % 
                                                                                                                      join(self.request.get('ti').split(','),
                                                                                                                           "','")
                                                                                                                      if self.request.get('ti') else '')))])
    resp = data_table.ToResponse(['timestamp'] + columns, (), self.request.get('tqx'))
    self.response.out.write(resp)


  def _mergeData(self, data):
    rv = []
    acc = {}
    prev_t = None
    for i in data:
      if prev_t is not None and datetime(i.timestamp.year, i.timestamp.month, i.timestamp.day) != prev_t:
        rv.append(acc)
        acc = {}
      acc['timestamp'] = datetime(i.timestamp.year, i.timestamp.month, i.timestamp.day)
      acc[i.tracked_item] = i.value
      prev_t = datetime(i.timestamp.year, i.timestamp.month, i.timestamp.day)

#      logging.debug(acc)

    logging.debug(rv)
    return rv
    

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
