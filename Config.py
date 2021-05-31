#from GoogleMercatorProjection import LatLng
import platform

bFullScreen = False # has to be True for R-Pi touchscreen version

# LOCATION(S)
# Further radar configuration (zoom, marker location) can be
# completed under the RADAR section
primary_coordinates = -121.95, 36.9764016   # Change to your Lat/Lon
location = primary_coordinates
darkPrefix ='https://api.darksky.net/forecast/'
openweatherPrefix = 'https://api.openweathermap.org/data/2.5/'
#primary_location = LatLng(primary_coordinates[0], primary_coordinates[1])

# Goes with light blue config (like the default one)
digitalcolor = "#50CBEB"
digitalformat = "{0:%I:%M\n%S %p}"  # The format of the time
digitalsize = 200
# The above example shows in this way:
#  https://github.com/n0bel/PiClock/blob/master/Documentation/Digital%20Clock%20v1.jpg
# ( specifications of the time string are documented here:
#  https://docs.python.org/2/library/time.html#time.strftime )

# digitalformat = "{0:%I:%M}"
# digitalsize = 250
#  The above example shows in this way:
#  https://github.com/n0bel/PiClock/blob/master/Documentation/Digital%20Clock%20v2.jpg


metric = 1  # 0 = English, 1 = Metric
radar_refresh = 10      # minutes
weather_refresh = 30    # minutes
home_refresh = 1        # temp and humidity at home
# Wind in degrees instead of cardinal 0 = cardinal, 1 = degrees
wind_degrees = True
# Depreciated: use 'satellite' key in radar section, on a per radar basis
# if this is used, all radar blocks will get satellite images
satellite = 0

# Language specific wording
LPressure = "Pressure "
LHumidity = "Humidity "
LWind = "Wind "
Lgusting = "Gusting "
LFeelslike = "Feels like "
LPrecip1hr = "Precip 1hr:"
LToday = "Today: "
LSunRise = "Sun Rise:"
LSet = " Set: "
LMoonPhase = " Moon:"
LInsideTemp = "Inside Temp "
LRain = " Rain: "
LSnow = " Snow: "


def get_node_addr():
    host = 'localhost'
    if platform.system() == 'Windows':
        node_port = '1234'
    else:
        node_port = '80'
    return host,node_port

