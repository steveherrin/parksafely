from __future__ import division                                                 
import psycopg2
import numpy as np
import pylab as P
from db_info import conn_string
from scipy.stats import linregress
from math import log
from operator import itemgetter
import sys

conn = psycopg2.connect(conn_string)

cur = conn.cursor()
cur2 = conn.cursor()

cur.execute("SELECT COUNT(*) FROM bicycle_parking")
n_bicycle = int(cur.fetchone()[0])

cur.execute("""SELECT incident_num,
                      ST_X(location),
                      ST_Y(location) FROM crimes
               WHERE vehicle='bicycle'
               AND EXTRACT(YEAR FROM t) >= 2013
               AND CAST(EXTRACT(DOY FROM t) AS int) % 2 = 1 """)

incident_num = cur.fetchone()[0]
x = float(cur.fetchone()[1])
y = float(cur.fetchone()[2])

location="ST_GeomFromText('POINT(%f %f)', 26943)"%(x, y)

extra_ds = []
risk_factors = []
extra_ds_safe = []
risk_factors_safe = []

max_d = float(sys.argv[2])
rate_weight = float(sys.argv[1])

for crime in cur:

  incident_num = crime[0]
  x = crime[1]
  y = crime[2]

  location="ST_GeomFromText('POINT(%f %f)', 26943)"%(x, y)

  cur2.execute("""SELECT SUM(n_racks)
                       FROM bicycle_parking 
                       WHERE ST_DWithin(location, %s, 200)"""%(location))
  try:
    n_racks = int(cur2.fetchone()[0])
  except TypeError:
    continue

  cur2.execute("""SELECT COUNT(*)
                  FROM crimes
                  WHERE vehicle='bicycle'
                    AND EXTRACT(YEAR from t) < 2013
                    AND ST_DWithin(crimes.location, %s, 200)"""%(location))
  n_crimes = int(cur2.fetchone()[0])

  rate_norm = n_crimes/n_racks

  cur2.execute("""SELECT bicycle_parking.id, 
                         ST_Distance(%s, location),
                         rate_norm,
                         rank 
                  FROM bicycle_parking
                  INNER JOIN (SELECT id, rate_norm, rank()
                    OVER (ORDER BY rate_norm DESC)
                    FROM bicycle_rates) AS rates
                  ON bicycle_parking.id = rates.id
                  WHERE ST_DWithin(%s, location, %%s)"""%(location,
                                                          location),
                  (300, ))

  markers = []
  for row in cur2:
    marker = {}                                                                 
    marker['id'] = int(row[0])
    marker['distance'] = float(row[1])
    marker['title'] = "ID %04i"%(row[0])
    marker['rate'] = row[2]
    marker['score'] = 100*row[3]/n_bicycle
    markers.append(marker)

  # TODO: Really makes sense to compare to closest?
  # The more sensible thing is to compare to the location itself.

  safest = max(markers, key=itemgetter('score'))
  closest = min(markers, key=itemgetter('distance'))

  #markers.remove(closest)

  markers.sort(key = lambda x: (x['rate']/rate_weight)**2 + (x['distance']/max_d)**2)

  extra_ds.append(markers[0]['distance'] - closest['distance'])
  risk_factors.append(markers[0]['rate']/closest['rate'])
  extra_ds_safe.append(safest['distance'] - closest['distance'])
  risk_factors_safe.append(safest['rate']/closest['rate'])

print extra_ds[:10]
print risk_factors[:10]

print "Using safest:"
print "  walk %0.3f more on average"%(np.mean(extra_ds_safe))
print "  risk is muliplied by %0.3e on average"%(np.mean(risk_factors_safe)) 
print "Using top pick:"
print "  walk %0.3f more on average"%(np.mean(extra_ds))
print "  risk is muliplied by %0.3e on average"%(np.mean(risk_factors)) 

