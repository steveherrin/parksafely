from __future__ import division
import psycopg2
from db_info import conn_string

conn = psycopg2.connect(conn_string)

bike_cur = conn.cursor()
cur = conn.cursor()

Ds = [10, 20, 40, 50, 80, 100, 160, 200]
Ns = [0 for d in Ds]
n_racks = 0

bike_cur.execute("SELECT id FROM bicycle_parking ORDER BY id")
for bike_rack_id in bike_cur:
    id = int(bike_rack_id[0])
    n_racks += 1

    #print "SELECT COUNT(*) FROM crimes, (SELECT location FROM bicycle_parking WHERE id=%s) AS bike WHERE vehicle='bicycle' AND ST_DWithin(bike.location, crimes.location, 10)"%(id,)
    #raw_input('..')

    for (i, d) in enumerate(Ds):

        cur.execute("""SELECT COUNT(*)
                    FROM crimes,
                    (SELECT location FROM bicycle_parking WHERE id=%s) AS bike
                    WHERE vehicle='bicycle'
                        AND ST_DWithin(bike.location, crimes.location, %s)""",
                    (id, d))
        Ns[i] +=  int(cur.fetchone()[0])

print "max_distance | average # crimes"
for (n, d) in zip(Ns, Ds):
    print d, n/n_racks
