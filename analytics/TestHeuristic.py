from __future__ import division
import psycopg2
import numpy as np
import config
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

db = db_interface.db_interface(host = config.DB_HOST,
                               user = config.DB_USER,
                               dbname = config.DB_NAME,
                               password = config.DB_PASSWORD)
cur = db.cursor

# Pick half of the bike crimes this year to test on
cur.execute("""SELECT incident_num,
                      ST_X(ST_Transform(location, 4326)) AS lon,
                      ST_Y(ST_Transform(location, 4326)) AS lat,
                      CAST(EXTRACT(DOY FROM t) AS int) %2
               FROM crimes
               WHERE vehicle='bicycle'
               AND NOT at_police_station
               AND EXTRACT(YEAR FROM t) >= 2013 """)

max_d = float(402.336)

r_w = float(sys.argv[1])

# Consider odd and even number days.
# Odd is used for testing and reported here.
# Even is the estimate of performance and goes into DB.
extra_ds = [[],[]]
risk_factors = [[],[]]
n_zeros = [0, 0]

for crime in cur:
    point = { 'lon' : float(crime[1]),
              'lat' : float(crime[2])}
    incident_num = crime[0]
    i = crime[3]

    parking = db.get_nearby_parking('bicycle', point, max_d)
    if len(parking) == 0:
        continue
    for spot in parking:
        spot['metric'] = abs(spot['distance']/250) + abs(spot['rate']/r_w)

    best = min(parking, key=itemgetter('metric'))
    closest = min(parking, key=itemgetter('distance'))

    extra_ds[i].append(best['distance'] - closest['distance'])

    rate_there = get_location_rate(db.cursor, point)
    #print best['rate'], best['distance'], rate_there

    if closest['rate'] == 0:
        n_zeros[i] +=1
        continue
    else:
        risk_factors[i].append(best['rate']/closest['rate'])

for i in xrange(2):
    extra_ds[i].sort(reverse = True)
    risk_factors[i].sort(reverse = True)

print "Using top pick:"
print "  walk %0.3f more on average"%(np.mean(extra_ds[1]))
print "  risk is muliplied by %0.3e on average"%(np.mean(risk_factors[1]))
print "  There were %i zeros."%(n_zeros[1])

db.cursor.execute(""" INSERT INTO recommendation_stats (rate_scale,
                                                     avg_extra_distance,
                                                     risk_ratio)
                      VALUES (%s, %s, %s) """,
                      (r_w, np.mean(extra_ds[0]), np.mean(risk_factors[0])))
db.connection.commit()

