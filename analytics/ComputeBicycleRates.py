from __future__ import division
import psycopg2
import numpy as np
import pylab as P
from db_info import conn_string
from scipy.stats import linregress
from math import log

conn = psycopg2.connect(conn_string)

outer_cur = conn.cursor()
inner_cur = conn.cursor()

max_d = 200 # meters

outer_cur.execute("TRUNCATE TABLE bicycle_rates")

outer_cur.execute("SELECT id FROM bicycle_parking ORDER BY id")
for bike_rack_id in outer_cur:
    id = int(bike_rack_id[0])

    # Normalize by just the spots there?
    # Could also do within a radius. Not sure. TODO
    inner_cur.execute("""SELECT SUM(n_racks)
                            FROM bicycle_parking AS bike, 
                            (SELECT location FROM bicycle_parking WHERE id=%s) AS bike2
                            WHERE ST_DWithin(bike.location, bike2.location, %s)""",
                            (id, max_d))
    n_racks = int(inner_cur.fetchone()[0])

    inner_cur.execute("""SELECT COUNT(*)
                            FROM crimes,
                            (SELECT location FROM bicycle_parking WHERE id=%s) AS bike
                            WHERE vehicle='bicycle' AND severity = 2
                            AND EXTRACT(YEAR FROM t) < 2013
                            AND ST_DWithin(bike.location, crimes.location, %s)""",
                        (id, max_d))
    n_severe = int(inner_cur.fetchone()[0])

    inner_cur.execute("""SELECT COUNT(*)
                            FROM crimes,
                            (SELECT location FROM bicycle_parking WHERE id=%s) AS bike
                            WHERE vehicle='bicycle' AND severity = 1
                            AND EXTRACT(YEAR FROM t) < 2013
                            AND ST_DWithin(bike.location, crimes.location, %s)""",
                        (id, max_d))
    n_other = int(inner_cur.fetchone()[0])

    rate = (n_severe + n_other)
    rate_severe = n_severe
    rate_other = n_other
    rate_norm = rate/n_racks
    rate_severe_norm = rate_severe/n_racks
    rate_other_norm = rate_other/n_racks

    inner_cur.execute("""INSERT INTO bicycle_rates (id, rate, rate_severe, rate_other,
                                                    rate_norm, rate_severe_norm,
                                                    rate_other_norm)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""", 
                                                    (id, rate, rate_severe, rate_other,
                                                    rate_norm, rate_severe_norm,
                                                    rate_other_norm))

    conn.commit()

conn.close()
