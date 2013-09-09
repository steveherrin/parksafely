from __future__ import division
import psycopg2
import numpy as np
from db_info import conn_string
from scipy.stats import linregress

conn = psycopg2.connect(conn_string)

bike_cur = conn.cursor()
cur = conn.cursor()

cur.execute("""DROP TABLE IF EXISTS bicycle_predictions""")
cur.execute("""CREATE TABLE bicycle_predictions
            (id int,
             rate real,
             predicted_rate real,
             foreign key (id) references bicycle_parking(id))""")
conn.commit()

max_d = 200 # meters
years = xrange(2003, 2012 + 1)

bike_cur.execute("SELECT id FROM bicycle_parking ORDER BY id")
for bike_rack_id in bike_cur:
    id = int(bike_rack_id[0])

    rate = [0 for year in years]


    for i, year in enumerate(years):

        cur.execute("""SELECT COUNT(*)
                   FROM crimes,
                   (SELECT location FROM bicycle_parking WHERE id=%s) AS bike
                   WHERE vehicle='bicycle'
                    AND ST_DWithin(bike.location, crimes.location, %s)
                    AND EXTRACT(YEAR FROM t) = %s""",
                    (id, max_d, year))
        n = int(cur.fetchone()[0])
        rate[i] = n

    slope, intercept, r_value, p_value, std_err = linregress(years, rate)
    #print "r_squared = %0.2e, p_value = %0.2e, std_err = %0.2e"%(r_value**2,
    #        p_value, std_err)
    #print "y = %e * x + %e"%(slope, intercept)
    prediction = lambda x: slope*x + intercept
    #print np.mean(rate), sum(rate)/(2012-2003)
    #raw_input('..')

    cur.execute("""INSERT INTO bicycle_predictions (id, rate, predicted_rate)
                    VALUES (%s, %s, %s)""", (id, sum(rate)/len(years), prediction(2013)))

    conn.commit()
