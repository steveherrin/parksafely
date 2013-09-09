#!/usr/bin/env python
from __future__ import division

from flask import Flask
from flask import g
from flask import jsonify
from flask import render_template
from flask import redirect
from flask import request
from flask import session
from flask import url_for
from operator import itemgetter

import psycopg2
import re
import my_db_config

# TODO: use Flask's config file support for this
DB_HOST = my_db_config.host
DB_NAME = my_db_config.name
DB_USER = my_db_config.user
DB_PASSWORD = my_db_config.password

MAPS_API_KEY = "AIzaSyAw2BGPy0yPzGmghf_a8P--TitjeFSXN68"
MAX_RESULTS = 5

app = Flask(__name__)
app.config.from_object(__name__)

app.debug = True

def connect_db():
  """ Returns a connection to the database
      made using setings in app.config
  """
  return psycopg2.connect(host = app.config['DB_HOST'],
                          dbname = app.config['DB_NAME'],
                          user = app.config['DB_USER'],
                          password = app.config['DB_PASSWORD'])

def get_db():
  """ Opens a new database connection if
      there isn't one already.
  """
  if not hasattr(g, 'db'):
    g.db = connect_db()
  return g.db

def get_cursor():
  """ Returns a cursor to the current
      database connection
  """
  db = get_db()
  return db.cursor()

@app.teardown_appcontext
def close_db(exception):
  """ Close the database connection. """
  if hasattr(g, 'db'):
    g.db.close()

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/about")
def about():
  return render_template('about.html')

@app.route("/contact")
def contact():
  return render_template('contact.html')

def get_n_bicycle():
  cur = get_cursor()
  cur.execute("SELECT COUNT(*) FROM bicycle_parking")
  return int(cur.fetchone()[0])

def get_max_rate():
  cur = get_cursor()
  cur.execute("SELECT MAX(rate_norm) FROM bicycle_rates")
  return float(cut.fetchone()[0])

def prettify_str(name):
  # Strip leading 0s from street addresses (e.g. 04th St)
  name = re.sub(r'(\s|^)0+', r' ', name)
  # Title case it
  name = name.title()
  # Fix title casing for ordinal numbers (e.g. 4Th)
  name = re.sub(r'[0-9][SNRT]', lambda m: m.group(0).lower(), name)
  # Fix title casing for possessive
  name = re.sub(r'\'S(\s|$)', lambda m: m.group(0).lower(), name)

  return name

def pick_name_address(name, address):
  """ Picks a name, address combination that makes sense
      given that either can be missing """
  if address == 'None':
    address = ""
  if 'undetermined' in name.lower():
    name = address
    address = ""
  return (name, address)

def get_nearby_bicycle(point, max_d):
  n_bicycle = get_n_bicycle()

  location = ("""ST_Transform(
                  ST_GeomFromText(
                      'POINT(%f %f)', 4326), 26943)"""
              %(point['lon'], point['lat']))
  query = ("""SELECT bicycle_parking.id,
                      ST_Distance(%s, location),
                      lon,
                      lat,
                      location_name,
                      address,
                      rate_norm,
                      rank
               FROM bicycle_parking INNER JOIN
                 (SELECT id, rate_norm, rank() OVER (ORDER BY rate_norm DESC)
                  FROM bicycle_rates) AS rates
               ON bicycle_parking.id = rates.id
               WHERE ST_DWithin(%s, location, %%s)
               ORDER BY ST_Distance(%s, location)"""
               %(location, location, location))
  cur = get_cursor()
  cur.execute(query, (max_d,))
  markers = []
  for row in cur:
    marker = {}
    marker['id'] = int(row[0])
    marker['distance'] = float(row[1])
    marker['longitude'] = float(row[2])
    marker['latitude'] = float(row[3])
    name = prettify_str(row[4])
    address = prettify_str(row[5])
    (marker['name'],
     marker['address']) = pick_name_address(name, address)
    marker['rate'] = row[6]
    marker['score'] = 100*row[7]/n_bicycle
    marker['note'] = ""
    markers.append(marker)
  return markers

@app.route("/search", methods=['GET'])
def search():
  try:
    point = {"lat": float(request.args['lat']),
             "lon": float(request.args['lon'])}
    max_d = float(request.args['max_d'])
  except ValueError:
    return jsonify(status = 'FAIL',
                   description = 'Could not parse arguments.')

  markers = get_nearby_bicycle(point, max_d)
  for marker in markers:
    if '444' in marker['address']:
      print marker
  if len(markers) > 0:
    safest = max(markers, key=itemgetter('score'))
    closest = min(markers, key=itemgetter('distance'))
    safest['note'] = "safest"
    closest['note'] = "closest"
    if (safest == closest):
      safest['note'] = 'safest and closest'

    markers.sort(key = lambda x: (x['rate']/5)**2 + (x['distance']/300)**2)
    suggested = markers[:5]
  else:
    suggested = []
  return jsonify(n = len(suggested), center = point,
                 status = "OK",
                 addresses = [x['address'] for x in suggested],
                 names = [x['name'] for x in suggested],
                 scores = ["%0.0f"%(x['score']) for x in suggested],
                 distances = ["%0.2f mi"%(x['distance']/1609.344) for x in suggested],
                 latitudes = [x['latitude'] for x in suggested],
                 longitudes = [x['longitude'] for x in suggested],
                 notes = [x['note'] for x in suggested]
                 )

@app.route("/map", methods=['GET'])
def map():
  return render_template("map.html")

if __name__ == "__main__":
  with app.test_request_context():
    print url_for('index')
    print url_for('search')
    print url_for('map')

  app.run()
