from __future__ import division
import psycopg2
import numpy as np
from db_info import conn_info
import db_interface
from operator import itemgetter
import sys

def get_location_rate(cur, point):
    location = ("ST_Transform(ST_GeomFromText('POINT(%f %f)', 4326), 26943)"
                    %(point['lon'], point['lat']))
    max_r = 200 #meters
    cur.execute("""SELECT SUM(n_spots)
                   FROM parking
                   WHERE ST_DWithin("""+location+""", location, %s)
                   AND (year_installed IS NULL OR
                        year_installed != 2013)""", (max_r,))
    try:
        n_nearby = int(cur.fetchone()[0])
    except TypeError:
        # edge case where there were no racks nearby. But clearly someone
        # parked there, so we'll count it as 1 spot
        n_nearby = 1

    cur.execute("""SELECT COUNT(*)
                   FROM crimes
                   WHERE crimes.vehicle='bicycle'
                   AND EXTRACT(YEAR FROM t) < 2013
                   AND ST_DWithin("""+location+""", location, %s)""",
                   (max_r, ))
    try:
        n_crimes = int(cur.fetchone()[0])
    except TypeError:
        n_crimes = 0

    return n_crimes/n_nearby

db = db_interface.db_interface(**conn_info)
cur = db.cursor

# Pick half of the bike crimes this year to test on
cur.execute("""SELECT incident_num,
                      ST_X(ST_Transform(location, 4326)) AS lon,
                      ST_Y(ST_Transform(location, 4326)) AS lat
               FROM crimes
               WHERE vehicle='bicycle'
               AND EXTRACT(YEAR FROM t) >= 2013
               AND CAST(EXTRACT(DOY FROM t) AS int) % 2 = 1 """)

max_d = float(402.336)

r_w = float(sys.argv[1])

extra_ds = []
risk_factors = []

for crime in cur:

    point = { 'lon' : float(crime[1]),
              'lat' : float(crime[2])}
    incident_num = crime[0]

    parking = db.get_nearby_parking('bicycle', point, max_d)
    if len(parking) == 0:
        continue
    for spot in parking:
        spot['metric'] = (spot['distance']/250)**2 + (spot['rate']/r_w)**2

    best = min(parking, key=itemgetter('metric'))
    closest = min(parking, key=itemgetter('distance'))

    extra_ds.append(best['distance'] - closest['distance'])

    rate_there = get_location_rate(db.cursor, point)
    #print best['rate'], best['distance'], rate_there

    if closest['rate'] == 0:
        continue
    else:
        risk_factors.append(best['rate']/closest['rate'])

extra_ds.sort(reverse = True)
risk_factors.sort(reverse = True)

print "Using top pick:"
print "  walk %0.3f more on average"%(np.mean(extra_ds))
print "  risk is muliplied by %0.3e on average"%(np.mean(risk_factors))

