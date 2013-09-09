import csv
import time
import json
import psycopg2
from db_info import conn_string

log = open('duplicates.txt', 'w')

def writeBikeParkingToDB(conn, lat, lon, placement, loc_name, 
                         address, n_racks, year_installed):
    """ Writes the rack to the database specified in conn, with the
        rest of the arguments giving the rack information. Returns the
        number of racks actually inserted (will be 0 if the rakcs's
        already in the database, for example). """

    cursor = conn.cursor()
    geom = "ST_GeometryFromText('POINT(%f %f)', 4326)"%(lon, lat)
    location = "ST_Transform(%s, 26943)"%(geom)

    try:
      cursor.execute("""INSERT INTO bicycle_parking
            (placement, location_name, address, n_racks,
             year_installed, lat, lon, location)
            VALUES (%s, %s, %s, %s, %s, %s, %s, """ + location + ")",
            (placement, loc_name, address, 
             n_racks, year_installed, lat, lon))
    except psycopg2.IntegrityError as e:
        conn.rollback()
        # Roll it back
        # Some bike racks are listed twice with no discernible differences
        cursor.execute("SELECT id, lat, lon, n_racks, year_installed, placement, location_name, address FROM bicycle_parking WHERE lat=%s AND lon=%s AND n_racks=%s", (lat, lon, n_racks));
        stored = cursor.fetchone()
        if str(stored[-1]) != address:
          log.write('-'*8 + '\n')
          log.write("(%f, %f) %i  %s %s %s %s\n"%(lat,lon,n_racks, year_installed,
                                            placement, loc_name, address))
          log.write("(%s, %s) %s  %s %s %s %s\n"%stored[1:])
        elif 'undetermined' in stored[-2].lower():
          cursor.execute("""UPDATE bicycle_parking
                            SET location_name=%s
                            WHERE id=%s""", (loc_name, stored[0]))
          conn.commit()
    else:
        conn.commit()
        return 1
    return 0

if __name__ == "__main__":

    conn = psycopg2.connect(conn_string)
    n_read = 0
    n_written = 0

    with open('data/Bicycle_Parking__Public_.csv') as file:
        reader = csv.DictReader(file, dialect='excel')
        for row in reader:
            if row['STATUS_DETAIL'] != 'INSTALLED':
                continue
            n_read += 1
            placement = row['PLACEMENT']
            lat = float(row['LATITUDE'])
            lon = float(row['LONGITUDE'])
            loc_name = row['LOCATION_NAME']
            address = row['ADDRESS']
            n_racks = int(row['RACKS_INSTALLED'])
            try:
                year_installed = int(row['YR_INSTALLED'])
            except ValueError:
                # Some racks have unknown installation year
                year_installed = None
            n_written += writeBikeParkingToDB(conn, lat, lon, placement,
                                              loc_name, address, n_racks,
                                              year_installed)

    print("Read %i entries."%(n_read))
    print("Wrote %i entries to DB."%(n_written))
    # So we can VACUUM
    conn.autocommit = True
    cursor = conn.cursor()
    # This is so Postgres makes use of the indexing.
    cursor.execute("VACUUM FULL ANALYZE bicycle_parking")

    # Print the database stsatus.
    cursor.execute("SELECT COUNT(*) FROM bicycle_parking")
    record = cursor.fetchone()
    print("Database now has %i entries."%(record[0]))

    cursor.close()
    conn.close()
