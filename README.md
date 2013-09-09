parksafely is a web app that recommends safe, nearby parking for
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
