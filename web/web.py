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

import pprint
import db_interface
import re

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_pyfile('config.cfg', silent=True)


def connect_db():
    """ Returns an interface to the database
        made using setings in app.config
    """
    return db_interface.db_interface(host=app.config['DB_HOST'],
                                     dbname=app.config['DB_NAME'],
                                     user=app.config['DB_USER'],
                                     password=app.config['DB_PASSWORD'])


def get_db():
    """ Returns a new database interface if
        there isn't one already.
    """
    if not hasattr(g, 'db'):
        g.db = connect_db()
    return g.db


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/about")
def about():
    return render_template('about.html')


@app.route("/contact")
def contact():
    return render_template('contact.html')


@app.route("/slides")
def slides():
    return render_template("slides.html",
                           embed_code=app.config['SLIDE_EMBED_CODE'])


def prettify_str(name):
    """ Makes street addresses look good """
    # Strip leading 0s from street addresses (e.g. 04th St)
    name = re.sub(r'(\s|^)0+', r' ', name)
    # Title case it
    name = name.title()
    # Fix title casing for ordinal numbers (e.g. 4Th)
    name = re.sub(r'[0-9][SNRT]', lambda m: m.group(0).lower(), name)
    # Fix title casing for possessive
    name = re.sub(r'\'S(\s|$|\W)', lambda m: m.group(0).lower(), name)
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


def format_parking_for_output(parking):
    """ Formats the data so that it looks good when shown
        to the end user """
    for spot in parking:
        spot['location_name'] = prettify_str(spot['location_name'])
        spot['address'] = prettify_str(spot['address'])
        (spot['location_name'],
         spot['address']) = pick_name_address(spot['location_name'],
                                              spot['address'])
        spot['safescore'] = "%0.0f" % (spot['safescore'])
        try:
            # 1 mile = 1609.344 m
            spot['distance'] = "%0.2f mi" % (spot['distance']/1609.344)
        except KeyError:
            pass
        # Don't waste bandwidth on these
        spot.pop('metric', None)
        spot.pop('rank', None)
        spot.pop('rate', None)
        spot.pop('id', None)
    return parking


def pref_to_scale(x):
    """ Transforms a -10 to +10 preference where -10
        is closer and +10 is safer to a scaling factor for the
        crime rate """
    # Somewhat arbitrarily chosen.
    # By eye, 0.25 produces a good balance
    return 0.25*pow(10, float(-x)/10)


@app.route("/stats_data")
def stats_data():
    """ Serves up all points and some tidbits
        in a JSON object for use in a big map """
    parking = get_db().get_all_parking('bicycle')
    # copy this because we want to return it separately
    most_dangerous = dict(max(parking, key=itemgetter('rate')))
    most_dangerous = format_parking_for_output([most_dangerous])[0]

    for spot in parking:
        spot['safescore'] = "%0.0f" % (spot['safescore'])
        spot.pop('rank', None)
        spot.pop('rate', None)
        spot.pop('address', None)
        spot.pop('location_name', None)
    return jsonify(status='OK',
                   n_parking=len(parking),
                   results=parking,
                   most_dangerous=most_dangerous)


@app.route("/search", methods=['GET'])
def search():
    """ Serves up a JSON object of the top MAX_RESULTS spots
        within max_d of point. """
    try:
        point = {"lat": float(request.args['lat']),
                 "lon": float(request.args['lon'])}
        max_d = float(request.args['max_d'])
        pref = float(request.args['preference'].lower())
    except ValueError:
        return jsonify(status='FAIL',
                       center=point,
                       description='Could not parse arguments.')
    rate_scale = pref_to_scale(pref)

    parking = get_db().get_nearby_parking('bicycle', point, max_d)
    for spot in parking:
        spot['metric'] = (abs(spot['distance']/250)
                          + abs(spot['rate']/rate_scale))
    if len(parking) > 0:
        safest = max(parking, key=itemgetter('safescore'))
        closest = min(parking, key=itemgetter('distance'))
        safest['safest'] = True
        closest['closest'] = True

        suggested = [closest]
        parking.remove(closest)

        # Basically we want a list of results that includes the closest,
        # and the remaning top-ranked ones, sorted in order of their rank
        # Reverse so pop() gets the lowest saferank (which is better)
        parking.sort(key=itemgetter('metric'), reverse=True)
        while len(parking) > 0 and len(suggested) < app.config['MAX_RESULTS']:
            suggested.append(parking.pop())
        suggested.sort(key=itemgetter('metric'))

        suggested = format_parking_for_output(suggested)
        return jsonify(status='OK',
                       center=point,
                       results=suggested,
                       n=len(suggested))
    else:
        return jsonify(status='NONE_FOUND',
                       center=point,
                       n=0,
                       description=("Found no results for location" +
                                    "and radius."))


@app.route("/map", methods=['GET'])
def map():
    return render_template("map.html")


@app.route("/stats")
def stats():
    n_crime = get_db().get_n_of_crime('bicycle')
    n_parking = get_db().get_n_of_parking('bicycle')
    # Get stats for default preference
    stats = get_db().get_recommendation_stats(0.5)
    return render_template("stats.html",
                           n_crime=n_crime,
                           n_parking=n_parking,
                           avg_extra_d=("%0.0f" %  # 1 meter = 3.281 ft
                                        (3.281*stats['avg_extra_distance'])),
                           risk_reduction = ("%0.1f" %
                                            (100*(1-stats['risk_ratio']))))


if __name__ == "__main__":
    app.run(host=app.config['HOST'],
            port=app.config['PORT'])
