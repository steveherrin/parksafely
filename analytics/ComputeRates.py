from __future__ import division
import psycopg2
import numpy as np
import config
import sys

conn = psycopg2.connect(host = config.DB_HOST,
                        user = config.DB_USER,
                        dbname = config.DB_NAME,
                        password = config.DB_PASSWORD)

outer_cur = conn.cursor()
inner_cur = conn.cursor()

max_d = 200 # meters
# Last year to include
last_year = int(sys.argv[1])

outer_cur.execute("TRUNCATE TABLE rates")

# Probably could stack subquerires inside of subqueries
# instead of looping, but this logic is clearer to me
outer_cur.execute(""" SELECT id, vehicle, location_name FROM parking
                      WHERE year_installed IS NULL
                      OR year_installed <= %s ORDER BY id""", (last_year,))
for parking_spot in outer_cur:
    id = int(parking_spot[0])

    # Normalize by the density of nearby spots
    inner_cur.execute("""SELECT SUM(n_spots)
                            FROM parking AS park1,
                            (SELECT location, vehicle FROM parking
                             WHERE id=%s) AS park2
                            WHERE ST_DWithin(park1.location, park2.location, %s)
                            AND park1.vehicle = park2.vehicle
                            AND (park1.year_installed IS NULL
                                 OR park1.year_installed <= %s)""",
                            (id, max_d, last_year))
    # Edge case where a lone rack was installed in 2013
    try:
        n_spots = int(inner_cur.fetchone()[0])
    except TypeError:
        rate = None
    else:
        inner_cur.execute("""SELECT COUNT(*),
                             SUM(POW(0.3, %s - EXTRACT(YEAR FROM t)))
                                FROM crimes,
                                (SELECT location, vehicle FROM parking WHERE id=%s) AS park
                                WHERE crimes.vehicle=park.vehicle
                                AND NOT at_police_station
                                AND EXTRACT(YEAR FROM t) <= %s
                                AND ST_DWithin(park.location, crimes.location, %s)""",
                            (last_year, id, last_year, max_d))
        result = inner_cur.fetchone()
        n_crimes = int(result[0])
        try:
            n_crimes_t = float(result[1])
        except TypeError:
            n_crimes_t = 0

        rate = n_crimes_t/n_spots

    inner_cur.execute("""INSERT INTO rates (id, rate)
                       VALUES (%s, %s)""", (id, rate))

    conn.commit()
conn.close()
