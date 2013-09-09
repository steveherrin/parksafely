from __future__ import division
import psycopg2
import numpy as np
import sys
from db_info import conn_string
from scipy.stats import linregress

conn = psycopg2.connect(conn_string)
cur = conn.cursor()

max_d = 200 # meters

if len(sys.argv) < 3:
    lat = float(raw_input('Latitude ? '))
    lon = float(raw_input('Longitude? '))
else:
    lat = float(sys.argv[1])
    lon = float(sys.argv[2])

#cur.execute("""SELECT MEDIAN(rate_norm),
#               MIN(rate_norm), 
#               MAX(rate_norm) FROM bicycle_rates""")
#median_rate, min_rate, max_rate = cur.fetchone()

#scale_rate = lambda x: 0.5*min(2, x/median_rate)

cur.execute("SELECT COUNT(*) FROM bicycle_parking")
n_bicycle = int(cur.fetchone()[0])

location = "ST_Transform(ST_GeomFromText('POINT(%f %f)', 4326), 26943)"%(lon, lat)
query = """SELECT id, ST_Distance(%s, location) FROM bicycle_parking
                WHERE ST_DWithin(%s, location, %%s)
                ORDER BY ST_Distance(%s, location)"""%(location,
                                                       location,
                                                       location)
cur.execute(query, (300,))
if cur.rowcount < 10:
    cur.execute(query, (500,))

racks = []
for bike_rack in cur:
    sub_cur = conn.cursor()

    sub_cur.execute("""SELECT rate_norm FROM bicycle_rates
                        WHERE id = %s""", (bike_rack[0],))
    rate = float(sub_cur.fetchone()[0])

    sub_cur.execute("""SELECT rank FROM
                        (SELECT id, rank() OVER (ORDER BY rate_norm DESC)
                         FROM bicycle_rates) AS ranked
                        WHERE id = %s""",
                        (bike_rack[0],))
    rank = int(sub_cur.fetchone()[0])
    
    racks.append((rate, float(bike_rack[1]), int(bike_rack[0]), rank))

r_scale = 4/max([x[0] for x in racks])
d_scale = 1/max([x[1] for x in racks])

scale_rate = lambda x: x

racks.sort(key = lambda x: x[1])
rack = racks[0]
print "Closest rack was id %i, d = %0.0f meters, rate = %0.4f, score = %0.2f"%(rack[2],
                                                                rack[1],
                                                                scale_rate(rack[0]), rack[3]/n_bicycle)

print "Printing 10 nearby, better racks:"
racks.sort(key = lambda x: ((x[0]*r_scale)**2 + (x[1]*d_scale)**2))
for rack in racks[:10]:
    print rack[2], scale_rate(rack[0]), rack[1], rack[3]/n_bicycle
