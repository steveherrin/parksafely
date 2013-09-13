import csv
import time
import json
import psycopg2
import requests
import config

log = open('duplicates.txt', 'w')
use_geocoding = False

use_SOCKS = False
session = requests.session()
if use_SOCKS:
    session.proxies = {'http': 'socks5://127.0.0.1:9999',
                       'https': 'socks5://127.0.0.1:9999'}



def writeBikeParkingToDB(conn, entry):
    """ Writes the rack to the database specified in conn, with the
        rest of the arguments giving the rack information. Returns the
        number of racks actually inserted (will be 0 if the racks's
        already in the database, for example). """

    cursor = conn.cursor()
    geom = "ST_GeometryFromText('POINT(%f %f)', 4326)"%(entry['lon'],
                                                        entry['lat'])
    location = "ST_Transform(%s, 26943)"%(geom)

    try:
      cursor.execute("""INSERT INTO parking (vehicle,
                                             description,
                                             location_name,
                                             address,
                                             n_spots,
                                             year_installed,
                                             location,
                                             lat,
                                             lon)
                        VALUES (%s, %s, %s, %s, %s, %s,"""
                                + location + ", %s, %s)",
                       ('bicycle', entry['description'], entry['location_name'],
                        entry['address'], entry['n_spots'],
                        entry['year_installed'], entry['lat'], entry['lon']))
    except psycopg2.IntegrityError as e:
        # Roll it back
        conn.rollback()

        # Let's see what we're dealing with
        cursor.execute("""SELECT id, description, location_name, address, n_spots, year_installed
                          FROM parking
                          WHERE lat=%s AND lon=%s AND vehicle = 'bicycle'""", (entry['lat'],
                                                                               entry['lon']));
        stored = cursor.fetchone()
        id = int(stored[0])
        log_it = stored[3].lower() != entry['address'].lower()
        if 'undetermined' in stored[2].lower():
            # If the location didn't have a name before, update it
            cursor.execute('UPDATE parking SET location_name=%s WHERE id=%s',
                           (entry['location_name'], id))
            log_it = False
        if stored[1] != entry['description'] or stored[5] != entry['year_installed']:
            # If they're described differently (street rack vs. lockers, e.g.)
            # Or if they weren't installed the same year,
            # assume they're different and update the number of spots
            if stored[1] != entry['description']:
                cursor.execute("UPDATE parking SET description = 'MIXED' WHERE id=%s", (id, ))
            cursor.execute('UPDATE parking SET n_spots=%s WHERE id=%s',
                           (int(entry['n_spots']) + int(stored[4]), id))
            log_it = False
        elif stored[4] > int(entry['n_spots']):
            # Assume that someone was just wrong about how many spots there were
            cursor.execute('UPDATE parking SET n_spots=%s WHERE id=%s',
                            (int(entry['n_spots']), id))
        if log_it:
            log.write('-'*10)
            log.write('%s %s %s %s %s %s'%(stored))
            log.write(str(entry))
            log.write('\n\n')

        conn.commit()
    else:
        conn.commit()
        return 1
    return 0

if __name__ == "__main__":

    conn = psycopg2.connect(host = config.DB_HOST,
                            user = config.DB_USER,
                            dbname = config.DB_NAME,
                            password = config.DB_PASSWORD)
    n_read = 0
    n_written = 0

    with open('data/Bicycle_Parking__Public_.csv') as file:
        reader = csv.DictReader(file, dialect='excel')
        for row in reader:
            if row['STATUS_DETAIL'] != 'INSTALLED':
                continue
            n_read += 1
            if n_read % 100 == 0:
              print n_read
            entry = {}
            entry['description'] = row['PLACEMENT']
            entry['lat'] = float(row['LATITUDE'])
            entry['lon'] = float(row['LONGITUDE'])
            entry['location_name'] = row['LOCATION_NAME']
            entry['address'] = row['ADDRESS']
            entry['n_spots'] = int(row['RACKS_INSTALLED'])
            try:
                entry['year_installed'] = int(row['YR_INSTALLED'])
            except ValueError:
                # Some racks have unknown installation year
                entry['year_installed'] = None
            if use_geocoding:
                if 'none' in entry['address'].lower():
                    address_for_geo = entry['location_name'] + ', San Francisco, CA'
                else:
                    address_for_geo = entry['address'] + ', San Francisco, CA'
                # Be careful; Google limits # of requests per day
                cur = conn.cursor()
                cur.execute("SELECT lat, lon FROM parking WHERE address LIKE %s", (address_for_geo,))
                if cur.rowcount > 0:
                    row = cur.fetchone()
                    entry['lat'] = row[0]
                    entry['lon'] = row[1]
                else:
                    params = {'sensor' : 'false'}
                    params['address'] = address_for_geo + ', San Francisco, CA'
                    r = session.get("http://maps.google.com/maps/api/geocode/json", params = params)
                    geo_data = json.loads(r.text)
                    #print geo_data
                    location = geo_data['results'][0]['geometry']['location']
                    try:
                        entry['lat'] = float(location['lat'])
                        entry['lon'] = float(location['lng'])
                    except Exception as e:
                        print geo_data
                        print n_read
                        raise e
                    time.sleep(0.1)

            n_written += writeBikeParkingToDB(conn, entry)

    print("Read %i entries."%(n_read))
    print("Wrote %i entries to DB."%(n_written))

    # So we can VACUUM
    conn.autocommit = True
    cursor = conn.cursor()
    # This is so Postgres makes use of the indexing.
    cursor.execute("VACUUM FULL ANALYZE parking")

    # Print the database stsatus.
    cursor.execute("SELECT COUNT(*) FROM parking")
    record = cursor.fetchone()
    print("Database now has %i entries."%(record[0]))

    cursor.close()
    conn.close()
