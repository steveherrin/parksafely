import psycopg2
from psycopg2.extras import DictCursor

class db_interface:
    def __init__(self, **kwargs):
        self.host = kwargs.get('host')
        self.dbname = kwargs.get('dbname')
        self.user = kwargs.get('user')
        self.password = kwargs.get('password')
        self._connection = None

    def __del__(self):
        if self._connection:
          self._connection.close()

    def _connect_db(self):
        """ Returns a connection to the database using
            the settings specified in the constructor """
        return psycopg2.connect(host = self.host,
                                dbname = self.dbname,
                                user = self.user,
                                password = self.password)

    @property
    def connection(self):
        """ Returns the database connection. If there isn't
            one already, create a new connection. """
        if not self._connection:
            self._connection = self._connect_db()
        return self._connection

    @property
    def cursor(self):
        """ Returns a cursor to the database. Handles connecting
            if the database isn't connected. """
        return self.connection.cursor()

    @property
    def dict_cursor(self):
        """ Returns a dict cursor to the database. Handles connecting
            if the database isn't connected. """
        return self.connection.cursor(cursor_factory=DictCursor)

    def get_n_parking(self, vehicle):
        """ Returns the total number of parking spots in
            the database for vehicle type"""
        cur = self.dict_cursor
        cur.execute("""SELECT COUNT(*) AS n FROM parking
                       WHERE vehicle=%s""", (vehicle,))
        return int(cur.fetchone()['n'])

    def get_max_rate(self, vehicle):
        """ Returns the maximum theft rate among all vehicle
            parking spots and the id of that spot """
        cur = self.dict_cursor
        cur.execute("""SELECT rate, id FROM rates
                       WHERE vehicle=%s
                       ORDER BY rate DESC
                       LIMIT 1""", (vehicle,))
        row = cur.fetchone()
        return float(row['rate']), int(row['id'])

    def get_nearby_parking(self, vehicle, point, max_d):
        """ Returns an array of dictionaries describing all parking
            spots of vehicle type within max_d of point. """

        # first convert point's lat/lon to the correct projection
        # used in the database
        location = ("""ST_Transform(ST_GeomFromText(
                       'POINT(%f %f)', 4326), 26943) """
                       %(point['lon'], point['lat']))

        query = ("""SELECT parking.id AS id,
                           ST_Distance(%s, location) AS distance,
                           lat,
                           lon,
                           location_name,
                           address,
                           rate,
                           rank
                    FROM parking NATURAL JOIN
                    (SELECT rates.id, rate, rank() OVER (ORDER BY rate DESC)
                           FROM rates) AS rates
                    WHERE ST_DWithin(%s, location, %%s)
                    AND (year_installed IS NULL OR year_installed < 2013)
                    AND vehicle=%%s
                    ORDER BY distance"""%(location, location))
        cur = self.dict_cursor
        cur.execute(query, (max_d, vehicle))

        parking = []
        n_parking = self.get_n_parking(vehicle)
        for row in cur:
            spot = dict(row)
            spot['safescore'] = 100*spot['rank']/n_parking
            parking.append(spot)
        return parking
