DROP INDEX IF EXISTS bicycle_rates_idx;
DROP TABLE IF EXISTS bicycle_rates;
DROP INDEX IF EXISTS bicycle_parking_gix;
DROP TABLE IF EXISTS bicycle_parking;

CREATE TABLE bicycle_parking (id serial UNIQUE,
			      placement text NOT NULL,
			      location_name text NOT NULL,
			      address text NOT NULL,
			      n_racks int NOT NULL,
			      year_installed int,
			      location geometry(Point, 26943) NOT NULL,
            lat double precision NOT NULL,
            lon double precision NOT NULL,
			      PRIMARY KEY (lat, lon, location_name, address, placement));

CREATE INDEX bicycle_parking_gix ON bicycle_parking USING GIST(location);

DROP TABLE IF EXISTS bicycle_rates;
CREATE TABLE bicycle_rates (id int,
                           rate double precision,
                           rate_severe double precision,
                           rate_other double precision,
                           rate_norm double precision,
                           rate_severe_norm double precision,
                           rate_other_norm double precision,
                           foreign key (id) references bicycle_parking(id));

CREATE INDEX bicycle_rates_idx ON bicycle_rates(id);

\d+ bicycle_parking;
\d+ bicycle_rates;
