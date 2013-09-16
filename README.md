Parksafely is a web app that recommends safe, nearby parking for
locations in San Francisco.

It uses a PostgreSQL database with PostGIS to store crime and parking
informaion from data provided by the city of San Francisco. This data
is then processed with Python and served up using Flask. The web app
also makes heavy use of the Google Maps API to visualize the data.

Repository Layout:

/analytics  : Scripts for analyzing the data for diagnostic purposes

/DB         : SQL scripts for initializing the database

/parse_data : Python scripts for parsing the SF data

/web        : The Flask-based application that actually serves up the app

Some scripts in parse_data and analytics depend on the db_interface.py script and config.cfg values in /web. You'll need to set up your environment for this, or create symbolic links.

The Flask script (web.py) also requires a configuration file. An example would be:

# Database settings

DB_HOST = 'localhost'

DB_NAME = '<db name>'

DB_USER = '<username>'

DB_PASSWORD = '<password>'

# Flask settings

DEBUG = True

HOST = '0.0.0.0'

PORT = 5000

# Things that go into the served pages

MAPS_API_KEY = "<Google Maps API Key"

SLIDE_EMBED_CODE = "<Slideshare embed code>"

USE_ANALYTICS = True

MAX_RESULTS = 5
