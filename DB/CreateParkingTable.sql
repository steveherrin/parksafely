DROP INDEX IF EXISTS rates_idx;
DROP TABLE IF EXISTS rates;
DROP INDEX IF EXISTS parking_gix;
DROP INDEX IF EXISTS parking_vix;
DROP TABLE IF EXISTS parking;

CREATE TABLE parking (id serial UNIQUE,
            vehicle vehicle_type NOT NULL,
			      description text NOT NULL,
			      location_name text NOT NULL,
			      address text NOT NULL,
			      n_spots int NOT NULL,
			      year_installed int,
			      location geometry(Point, 26943) NOT NULL,
            lat double precision NOT NULL,
            lon double precision NOT NULL,
            primary key (id),
            unique (lat, lon, vehicle));

CREATE INDEX parking_gix ON parking USING GIST(location);
CREATE INDEX parking_vix ON parking(vehicle);

DROP TABLE IF EXISTS rates;
CREATE TABLE rates (id int,
                    rate double precision,
                    foreign key (id) references parking(id));

CREATE INDEX rates_idx ON rates(id);

\d+ parking;
\d+ rates;
