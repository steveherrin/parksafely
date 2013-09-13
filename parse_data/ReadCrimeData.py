import csv
import xml.etree.ElementTree as ET
import psycopg2
import glob
import config

def writeCrimeToDB(conn, incident_num, vehicle, severity, date, time, lat, lon, address):
    """ Writes the crime to the database specified in conn, with the
        rest of the arguments giving the crime information. Returns the
        number of crimes actually inserted (will be 0 if the crime's
        already in the database, for example). """

    cursor = conn.cursor()
    timestamp = date + " " + time + " America/Los_Angeles"
    geom = "ST_GeometryFromText('POINT(%f %f)', 4326)"%(lon, lat)
    location = "ST_Transform(%s, 26943)"%(geom)
    at_police_station = (address == '800 Block of BRYANT ST')
    try:
        cursor.execute("""INSERT INTO crimes
            (incident_num, t, vehicle, severity,
             location, address, at_police_station)
            VALUES (%s, %s, %s, %s, """ + location + ", %s, %s)",
            (incident_num, timestamp, vehicle,
             severity, address, at_police_station))
    except psycopg2.IntegrityError:
        # First, roll it back
        conn.rollback()
        # Motorcycle and truck thefts are listed twice
        # Trucks are lumped in with cars, but motorcycles
        # are not, so deal with that.
        if vehicle == 'motorcycle':
            cursor.execute("""UPDATE crimes SET vehicle = %s
                WHERE incident_num = %s""", (vehicle, incident_num))
            conn.commit()
        else:
            # Some incident numbers show up twice, years after they
            # first showed up. Not sure if that's an update or what,
            # But we'll just ignore those since there are few.
            pass
    else:
        conn.commit()
        return 1
    return 0

def getCrimeInfo(descript):

    descript = descript.upper()

    # Description of crime, vehicle type, severity
    # Description is as used by the SFPD
    # Vehicle type is bicycle, automobile, or motorcycle
    # Severity is assigned semi-arbiratily, with outright theft at 2
    crimes = (('THEFT BICYCLE', 'bicycle', 2),
            ('ATTEMPTED THEFT OF A BICYCLE', 'bicycle', 1),
            ('THEFT FROM UNLOCKED VEHICLE', 'automobile', 1),
            ('THEFT FROM LOCKED VEHICLE', 'automobile', 1),
            ('THEFT FROM UNLOCKED AUTO', 'automobile', 1),
            ('THEFT FROM LOCKED AUTO', 'automobile', 1),
            ('THEFT AUTO STRIP', 'automobile', 1),
            ('STOLEN AUTOMOBILE', 'automobile', 2),
            ('STOLEN MOTORCYCLE', 'motorcycle', 2),
            ('STOLEN TRUCK', 'automobile', 2),
            ('VANDALISM OF VEHICLES', 'automobile', 1),
            ('ARSON OF A VEHICLE', 'automobile', 2))

    for crime in crimes:
        if crime[0] in descript:
            return {'vehicle': crime[1], 'severity': crime[2]}
    return None


if __name__ == "__main__":

    conn = psycopg2.connect(host = config.DB_HOST,
                            user = config.DB_USER,
                            dbname = config.DB_NAME,
                            password = config.DB_PASSWORD)
    n_csv = 0
    n_kml = 0

    for file_name in glob.iglob("data/sfpd_incident_*.csv"):
        with open(file_name) as file:
            reader = csv.DictReader(file, dialect='excel')
            for row in reader:
                info = getCrimeInfo(row["Descript"])
                if info:
                    # Don't care about out of town crimes
                    if row["Location"] == "OUT OF TOWN":
                        continue

                    incident_num = row["IncidntNum"]
                    date = row["Date"]
                    time = row["Time"]
                    lat = float(row["Y"])
                    lon = float(row["X"])
                    address = row['Location']

                    n_csv += writeCrimeToDB(conn, incident_num, info['vehicle'],
                                    info['severity'], date, time, lat, lon, address)

    for file_name in glob.iglob("data/CrimeIncident90*.kml"):
        tree = ET.parse(file_name)
        root = tree.getroot()

        prefix = './/{http://www.opengis.net/kml/2.2}'
        for Placemark in root.findall(prefix + "Placemark"):
            ExtendedData = Placemark.find(prefix + "ExtendedData")
            row = {}
            for SimpleData in ExtendedData.findall(prefix + "SimpleData"):
                row[SimpleData.get('name')] = SimpleData.text

            info = getCrimeInfo(row['Description'])

            if info:
                incident_num = row["Incident"]
                date = row["Date"]
                time = row["Time"]
                point = Placemark.find(prefix + 'Point')
                coord = point.find(prefix + 'coordinates').text.split(',')
                lat = float(coord[1])
                lon = float(coord[0])
                address = None # TODO: Fix this

                n_kml += writeCrimeToDB(conn, incident_num, info['vehicle'],
                            info['severity'], date, time, lat, lon, address)

    print("Read %i entries."%(n_csv + n_kml))
    print("  %i from the csv files."%(n_csv))
    print("  %i from the kml files."%(n_kml))

    # So we can VACUUM
    conn.autocommit = True
    cursor = conn.cursor()
    # This is so Postgres makes use of the indexing.
    cursor.execute("VACUUM FULL ANALYZE crimes")

    # Summarize the database status.
    cursor.execute("SELECT COUNT(*) FROM crimes")
    record = cursor.fetchone()
    print("Database now has %i entries."%(record[0]))

    cursor.close()
    conn.close()
