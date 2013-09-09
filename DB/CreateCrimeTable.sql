DROP TABLE IF EXISTS crimes;
DROP TYPE IF EXISTS vehicle_type;

CREATE TYPE vehicle_type AS ENUM('bicycle',
                                 'motorcycle',
                                 'automobile');

CREATE TABLE crimes (incident_num int primary key,
                     t timestamp with time zone NOT NULL,
                     vehicle vehicle_type NOT NULL,
                     severity int NOT NULL,
                     location geometry(POINT, 26943) NOT NULL);
                     
CREATE INDEX crimes_gix ON crimes USING GIST(location);
CREATE INDEX crimes_timeidx ON crimes(t);

\d+ crimes;
