DROP TABLE IF EXISTS recommendation_stats;

CREATE TABLE recommendation_stats ( id serial primary key,
                                    rate_scale double precision unique,
                                    avg_extra_distance double precision,
                                    risk_ratio double precision );
