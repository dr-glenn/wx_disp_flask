# -*- coding: utf-8 -*-                 # NOQA
# OpenWeather data provider.
# It returns current forecast for the next week
# This page describes the values returned: https://darksky.net/dev/docs#api-request-types
# Or just look at this page for an example: https://darksky.net/dev/docs

from urllib.request import urlopen,Request
from urllib.parse import urlencode
import json
import datetime as dt
import os

from flask import url_for

import Config
import ApiKeys
import logging
import my_logger
from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape
import tail
import timeplot
import tzinfo_4us as tzhelp

from Config import get_node_addr
from sensor_in import read_log, sensor_devs

logger = my_logger.setup_logger(__name__, '../ow.log', level=logging.DEBUG)

# units for values: temperature, wind
METRIC=0
US=1

def c_to_f(temp):
    return 1.8 * temp + 32.0

Eastern  = tzhelp.USTimeZone(-5, "Eastern",  "EST", "EDT")
Central  = tzhelp.USTimeZone(-6, "Central",  "CST", "CDT")
Mountain = tzhelp.USTimeZone(-7, "Mountain", "MST", "MDT")
Pacific  = tzhelp.USTimeZone(-8, "Pacific",  "PST", "PDT")

myTZ = {'-5':Eastern, '-6':Central, '-7': Mountain, '-8':Pacific}

def make_buttons(exclude=[], lon_lat=None, home_name='', tzoff=-8, radar_type=''):
    '''
    Make page change buttons, but exclude some.
    Button names are the same as page routes.
    :param exclude: list of button names to exclude
    :return: DIV that contains fully constructed buttons
    '''
    buttons = []
    NAV_BUT = {}
    #NAV_BUT['radar']    = ('Radar', get_node_addr(), 'radar.html')  # radar is a node.js page
    NAV_BUT['radar']    = ('Radar', None, 'static/radar.html')  # radar is a node.js page
    NAV_BUT['now']      = ('Current Wx', None, 'now')           # this is a flask page
    NAV_BUT['hourly']   = ('Today Fcst', None, 'hourly_divs')   # this is a flask page
    NAV_BUT['daily']    = ('Daily Fcst', None, 'daily')         # this is a flask page

    # construct the request args if any
    args = {}
    if lon_lat:
        args['lon_lat'] = lon_lat
    if home_name and len(home_name) > 0:
        args['home_name'] = home_name
    if tzoff:
        args['tz'] = tzoff
    if radar_type and len(radar_type) > 0:
        args['radar_type'] = radar_type
    req_args = urlencode(args)
    logger.debug('make_buttons: req = {}'.format(req_args))
    for key in exclude:     # some of the buttons should not be present on the page
        NAV_BUT.pop(key)
    for key,item in NAV_BUT.items():
        if not item[1]:
            # create link to local page
            link = '/{}?{}'.format(item[2],req_args)
        else:
            # create link to other site page
            link = 'http://{}:{}/{}?{}'.format(item[1][0], item[1][1], item[2], req_args)
        bstr = '<a href="{}"><button>{}</button></a>'.format(link,NAV_BUT[key][0])
        buttons.append(bstr)
    return buttons

'''
OpenWeather defines some strings to describe weather icons,
See page for more info: https://openweathermap.org/weather-conditions#Weather-Condition-Codes-2
In the 'weather' entry a text description is returned as well as 'icon' name.
The same icon may be used for variations on the conditions, e.g., "light rain" and "very heavy rain"
have same icon - so you need to display the text also.
And there are day and night icons: same numeric code for icon, with suffix 'd' or 'n'.
'''

# datetime values need special handling
dt_keys = ('dt', 'sunrise', 'sunset', 'day_name', 'hour_name')

def metric_to_english(key, value):
    '''
    Some values should be converted.
    :param key:
    :param value:
    :return: converted value as a number and units string
    '''
    #logger.debug('metric_to_english: key={}, value={}'.format(key,value))
    if key.startswith('temp') or key.startswith('feels_like'):
        return c_to_f(float(value)),'°F'
    elif key == 'wind_speed' or key == 'wind_gust':
        return 2.237 * float(value),'mph'    # meters/sec to miles/hour
    else:
        return value,' '

class DataParse:
    '''
    Abstract Class.
    Child classes: CurrentObs, FcstHourlyData, FcstDailyData.
    Parses JSON returned from Wunderground according to a list of keys.
    We request current observations and hourly and daily forecasts.
    Each of these items contains different sets of data with different keys.
    Once the data is parsed, the application can then request that the
    data be returned as a string, ready for display.
    '''
    def __init__(self,wxdata,dataKeys,tzoff=-8):
        logger.debug('DataParse: tzoff={}'.format(tzoff))
        tzoffStr = str(tzoff)
        if tzoffStr in myTZ:
            tz_local = myTZ[tzoffStr]
        else:
            tz_local = None     # we won't be able to correct times that are returned by OpenWeather
        self.obs = {}
        for key in dataKeys:
            if isinstance(key[1],(list,tuple)):
                try:
                    # TODO: only handles tuple of 2 elements, no more.
                    kk = key[1]
                    # OpenWeather puts a dict inside a list for 'current',
                    # but not for 'daily'!
                    if isinstance(wxdata[kk[0]], (list,tuple)):
                        data_dict = wxdata[kk[0]][0]    # get the dict
                    else:
                        # assume it is a dict
                        data_dict = wxdata[kk[0]]
                    data = data_dict[kk[1]]
                except:
                    logger.error('key=%s, wxdata=%s' %(str(kk),str(wxdata[kk[0]])))
            else:
                if key[1] in wxdata:
                    data = wxdata[key[1]]
                    if key[1] in dt_keys:
                        # storing a datetime
                        if tz_local:
                            tz_x = dt.timezone(dt.timedelta(hours=tzoff))
                            tdata = dt.datetime.fromtimestamp(data,tz=tz_x)
                            offset = 0
                            #logger.debug('time={}, offset={}'.format(tdata,offset))
                            offset = tz_local.utcoffset(tdata)  # figures out offset based on tdata - might be wrong near when daylight time changes
                            #logger.debug('time={}, offset={}'.format(tdata,offset))
                            #tzobj = dt.timezone(dt.timedelta(hours=offset))
                            tzobj = dt.timezone(offset)
                        else:
                            tzobj = None
                        data = dt.datetime.fromtimestamp(data,tzobj)
                        if key[1] == 'dt':
                            # 'dt' is time of current obs or future forecast. Get day and hour from it for display use.
                            self.obs['day_name'] = [data.strftime('%A'),'']
                            #logger.debug('store dt={}, day={}'.format(str(data),data.strftime('%A')))
                            self.obs['hour_name'] = [data.strftime('%I'),' '+data.strftime('%p')]
                        elif key[1] in ('sunrise', 'sunset'):

                            #logger.debug('sunrise/sunset: {}'.format(str(data)))
                            data = data.strftime('%I:%M %p')
                            #logger.debug('sunrise/sunset: {}'.format(str(data)))
                            pass
                    #logger.debug('key=%s, data=%s' %(key[1],str(data)))
                else:
                    # DarkSky has optional fields, so it's OK if key[1] not found
                    logger.info('DataParse: key=%s not present in wxdata' %(key[1]))
                    continue
            if key[2] == -1 or key[2] == Config.metric:
                # TODO: should probably eliminate key[2]: column 3
                # Config.metric has value of either 0 or 1
                self.obs[key[0]] = [data,key[3]]
                #logger.debug('save obs: key=%s, value=%s' %(key[0],str(self.obs[key[0]])))
            else:
                # key[2] != Config.metric, so skip this obs
                # NOTE: this clause only applied to wunderground, which returned some data
                # in both metric and US. OpenWeatherMap only returns one or the other - as requested.
                pass

    def getObsStr(self, key, units=US):
        '''
        Get value from wxdata and append units string
        :param key:
        :param units:
        :return: a string for display
        '''
        if key in self.obs:
            # TODO: the obs tables should have a conversion function
            unitStr = None
            if key in dt_keys:
                # must interpret as str, this is really important when fetching hour_name
                obsVal = self.obs[key][0]
            else:
                try:
                    # attempt numeric conversion
                    obsVal = float(self.obs[key][0])
                    if units==US:
                        obsVal,unitStr = metric_to_english(key,obsVal)
                    if abs(obsVal) >= 10.0:
                        obsVal = int(obsVal + 0.5)  # get rid of decimal places
                    else:
                        obsVal = float('%.1f' %(obsVal))
                except:
                    # could not convert to float, so assume it's a string
                    obsVal = self.obs[key][0]
            if not unitStr: # None or empty ''
                unitStr = self.obs[key][1]
            retval = str(obsVal) + unitStr
            return retval
        else:
            logger.warning('key=%s not found' %(key))
            return None

    def getObsVal(self, key, units=US):
        # Get value from wxdata + the appropriate units string
        if key in self.obs:
            unitStr = ''
            if key in dt_keys:
                # must interpret as str, this is really important when fetching hour_name
                obsVal = self.obs[key][0]
            else:
                # TODO: the obs tables should have a conversion function
                try:
                    obsVal = float(self.obs[key][0])
                    if units==US:
                        obsVal,unitStr = metric_to_english(key,obsVal)
                    if abs(obsVal) >= 10.0:
                        obsVal = int(obsVal + 0.5)  # get rid of decimal places
                    else:
                        obsVal = float('%.1f' % (obsVal))
                except:
                    # could not convert to float, so assume it's a string
                    obsVal = self.obs[key][0]
            retval = str(obsVal)
            return retval,unitStr
        else:
            logger.warning('key=%s not found' % (key))
            return None,''

    @classmethod
    def wind_compass(cls, degrees):
        '''
        Convert direction in degrees to compass direction, e.g., 135 to SE
        '''
        # divide into 8 zones
        compass_center = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N']
        degree_center = [0, 45, 90, 135, 180, 225, 270, 315, 360]
        # round off degrees to nearest center
        degrees = (float(degrees) + 22.5) % 360    # to wrap around at zero degrees
        degree_idx = int(degrees / 45)   # number from 0 to 7
        return compass_center[degree_idx]


class CurrentObs(DataParse):
    # Lookup table for key used in application display,
    # key used in wxdata returned by wunderground,
    # metric=1 or English=0 units or no_units=-1
    # and displays units (if any) in the application
    # NOTE: must use 'current' node to fetch these
    '''
    app_key: the name used in my code to get the value
    data_key: the name or tuple used to get the value from JSON
      if data_key is a tuple, then value is a nested dict
    metric: 1 if value is metric, 0 if US, -1 if no units or no conversion
    units: string to append to value when displayed
    '''
    obsKeys = [
        # app_key,              data_key,           metric, units
        ('datetime',            'dt',               -1, ''),
        ('sunrise',             'sunrise',          -1, ''),
        ('sunset',              'sunset',           -1, ''),
        ('temp',                'temp',             1, u'°C'),
        ('feels_like',          'feels_like',       1, u'°C'),
        ('pressure',            'pressure',         1, ' mb'),
        ('humidity',            'humidity',         -1, '%'),
        ('dew_point',           'dew_point',        1, u'°C'),
        ('cloud_cover',         'clouds',           -1, '%'),
        ('uv_index',            'uvi',              -1, ''),
        ('visibility',          'visibility',       -1, ' m'),
        ('wind_speed',          'wind_speed',       1, ' m/s'),
        ('wind_gust',           'wind_gust',        1, ' m/s'),
        ('wind_deg',            'wind_deg',         -1, ''),
        ('rain_1h',             '(rain,1h)',        1, ' mm'),
        ('snow_1h',             '(snow,1h)',        1, ' mm'),
        ('weather_id',          ('weather','id'),   -1, ''),   # integer
        ('weather_main',        ('weather','main'), -1, ''),   # category, such as Rain, Snow
        ('weather_description', ('weather','description'), -1, ''), # text
        ('weather_icon',        ('weather','icon'), -1, ''),   # name of icon to fetch
    ]
    # other keys: precipProbability, precipType, dewPoint, cloudCover, uvIndex, visibility, ozone
    def __init__(self, wxdata, tzoff=-8):
        #print(wxdata['current'])
        logger.debug('CurrentObs: tzoff={}'.format(tzoff))
        DataParse.__init__(self,wxdata['current'],self.obsKeys, tzoff)

class FcstDailyData(DataParse):
    # Lookup table for key used in application display,
    # key used in wxdata returned by wunderground,
    # metric=1 or English=0 units,
    # and displays units (if any) in the application
    # NOTE: must use 'daily/data' node to fetch these
    obsKeys = [
        # app_key,              data_key,           metric, units
        ('datetime',            'dt',               -1, ''),
        ('sunrise',             'sunrise',          -1, ''),
        ('sunset',              'sunset',           -1, ''),
        ('temp_day',            ('temp','day'),     1, u'°C'),
        ('temp_min',            ('temp','min'),     1, u'°C'),
        ('temp_max',            ('temp','max'),     1, u'°C'),
        ('temp_night',          ('temp','night'),   1, u'°C'),
        ('temp_eve',            ('temp','eve'),     1, u'°C'),
        ('temp_morn',           ('temp','morn'),    1, u'°C'),
        ('feels_like_day',      ('feels_like','day'), 1, u'°C'),
        ('feels_like_night',    ('feels_like','night'), 1, u'°C'),
        ('feels_like_eve',      ('feels_like','eve'), 1, u'°C'),
        ('feels_like_morn',     ('feels_like','morn'), 1, u'°C'),
        ('pressure',            'pressure',         1, ' mb'),
        ('humidity',            'humidity',         -1, '%'),
        ('dew_point',           'dew_point',        1, u'°C'),
        ('wind_speed',          'wind_speed',       1, ' m/s'),
        ('wind_deg',            'wind_deg',         -1, ''),
        ('weather_id',          ('weather','id'),   -1, ''),   # integer
        ('weather_main',        ('weather','main'), -1, ''),   # category, such as Rain, Snow
        ('weather_description', ('weather','description'), -1, ''), # text
        ('weather_icon',        ('weather','icon'), -1, ''),   # name of icon to fetch
        ('cloud_cover',         'clouds',           -1, '%'),
        ('uv_index',            'uvi',              -1, ''),
        ('pop',                 'pop',              -1, ''),
    ]
    # other keys: sunriseTime, sunsetTime, moonPhase, precipIntensityMax, precipIntensityMaxTime, more
    def __init__(self,wxdata,iday, tzoff=-8):
        if len(wxdata['daily']) > iday:
            DataParse.__init__(self,wxdata['daily'][iday],self.obsKeys, tzoff)

class FcstHourlyData(DataParse):
    # Lookup table for key used in application display,
    # key used in wxdata returned by wunderground,
    # metric=1 or English=0 units,
    # and displays units (if any) in the application
    # NOTE: must use 'hourly/data' node to fetch these
    obsKeys = [
        # app_key,              data_key,           metric, units
        ('datetime',            'dt',               -1, ''),
        ('temp',                'temp',             1, u'°C'),
        ('feels_like',          'feels_like',       1, u'°C'),
        ('pressure',            'pressure',         1, ' mb'),
        ('humidity',            'humidity',         -1, '%'),
        ('dew_point',           'dew_point',        1, u'°C'),
        ('wind_speed',          'wind_speed',       1, ' m/s'),
        ('wind_deg',            'wind_deg',         -1, ''),
        ('weather_id',          ('weather','id'),   -1, ''),   # integer
        ('weather_main',        ('weather','main'), -1, ''),   # category, such as Rain, Snow
        ('weather_description', ('weather','description'), -1, ''), # text
        ('weather_icon',        ('weather','icon'), -1, ''),   # name of icon to fetch
        ('cloud_cover',         'clouds',           -1, '%'),
        ('uv_index',            'uvi',              -1, ''),
        ('pop',                 'pop',              -1, ''),
    ]
    # other keys: apparentTemperature, dewPoint, humidity, pressure, windSpeed, windGust, windBearing, cloudCover, uvIndex, visibility, ozone
    def __init__(self,wxdata,ihour, tzoff=-8):
        DataParse.__init__(self,wxdata['hourly'][ihour],self.obsKeys,tzoff)

# I think this is only used for testing
def make_html(obs, hourly, daily, heading='Current'):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    path = os.path.join(os.path.dirname(__file__), 'templates')
    loader = FileSystemLoader(searchpath=path)
    env = Environment(loader=loader)
    templ = env.get_template('wx_now_all.html')
    ihour = 12
    iday = 1    # tomorrow
    obs_vals = [[key,obs.getObsStr(key)] for key in obs.obs]
    hourly_vals = [[key,hourly.getObsStr(key)] for key in hourly.obs]
    daily_vals = [[key,daily.getObsStr(key)] for key in daily.obs]
    return templ.render(heading=heading, obs=obs_vals, hourly=hourly_vals, hour_name='13', daily=daily_vals, daily_name='Someday')

def get_home_sensors(fname, sys_name='gn-pi-zero-1'):
    '''
    Read latest lines from sensor logfiles. Search for match with sys_name.
    Parse the lines which have been written in my custom text format.
    :param fname: logfile written by process mqtt_rcv.py
    :param sys_name: computer name for sensors
    :return: dict that contains sensor names as key to values. Values are strings
    '''
    val_dict = {}
    f = open(fname, 'r')
    sens_str = tail.tail(f, lines=4)
    sens_lines = sens_str.split('\n')
    # lines look like this:
    # gn_home/gn-pi-zero-1/pm25: time=2021-05-03T14:31:01,PM1.0=2,PM2.5=4,PM10.0=9
    # gn_home/gn-pi-zero-1/bme280: time=2021-05-03T14:31:06,temp_c=21.2,humidity=44.7,pressure=1008.1
    for line in sens_lines:
        l = line.split(':',maxsplit=1)
        if sys_name and l[0].find(sys_name) == -1:
            # might have readings from more than one sensor computer
            # don't yet have a proper way to handle that, so only accept one of them
            continue
        # l[0] is the sensor topic
        # l[1] is the values, including time
        logger.debug('get_home_sensors: sensor={}'.format(l[0]))
        values_list = l[1].split(',')
        # stuff the values_list into a dict
        for value in values_list:
            logger.debug('get_home_sensors: value={}'.format(value))
            try:
                val = value.split('=')
                sens_key = val[0].strip().lower().replace('.','_') + '_sens'
                sens_val = val[1]
                if sens_key == 'time_sens':
                    dt_obs = dt.datetime.strptime(sens_val, '%Y-%m-%dT%H:%M:%S')
                    sens_val = dt_obs.strftime('%I:%M %p') # only want HH:MM for display
                    units = ''
                else:
                    sens_val,units = metric_to_english(sens_key, sens_val)
                    #logger.debug('get_home_sensors: metric_to_english={},{}'.format(sens_val,units))
                    if l[0].find('bme280') != -1:
                        # bme280 returns float values
                        sens_val = '{:.1f}'.format(float(sens_val))
                    elif l[0].find('pm25') != -1:
                        # pm25 returns integers
                        pass
            except Exception as e:
                logger.debug('ERROR: get_home_sensors: value={}'.format(value))
                #logger.debug(e)
            val_dict[sens_key] = sens_val
    logger.debug('get_home_sensors: {}'.format(str(val_dict)))
    return val_dict

def get_latest_sensors(sensors):
    '''
    Collect most recent values of all sensors.
    :param sensors: dict of SensorVals, e.g., BME280, PM25
    :return: dict with sensor as key and current value
    '''
    sens_vals = {}   # key is sensor name
    for s in sensors:
        for dev in sensors[s].vals:
            logger.debug('get_latest_sensors: {}, {}'.format(s, dev))
            sens_vals[dev+'_sens'] = sensors[s].vals[dev][-1]
    logger.debug('latest sensors: {}'.format(str(sens_vals)))
    return sens_vals

def make_wx_current(the_vals, heading='Current Obs', tzoff=-8, lon_lat=None, home_name='', radar_type=''):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    if False:
        env = Environment(
            loader=PackageLoader("app"),
            autoescape=select_autoescape()
        )
    else:
        path = os.path.join(os.path.dirname(__file__), 'templates')
        loader = FileSystemLoader(searchpath=path)
        env = Environment(loader=loader)
    templ = env.get_template('wx_now.html')
    templ_keys = ['temp', 'humidity', 'feels_like', 'wind_speed', 'wind_deg', 'weather_description', 'weather_icon', 'sunrise', 'sunset', 'uv_index', 'feels_like']
    templ_args = {}
    # load all values from the forecast or obs
    for key in templ_keys:
        templ_args[key],unit = the_vals.getObsVal(key,units=US)
        if key == 'wind_deg':
            templ_args['wind_compass'] = DataParse.wind_compass(templ_args['wind_deg'])
    dt_obs = dt.datetime.fromisoformat(the_vals.getObsVal('datetime')[0])
    # these templ_args are derived and not from forecast provider
    day_name = dt_obs.date().strftime('%A') # day-of-week name
    templ_args['day_name'] = day_name
    templ_args['time'] = dt_obs.strftime('%I:%M %p')
    templ_args['heading'] = heading
    if home_name:
        templ_args['home_name'] = home_name
    # Get home sensors
    read_log('../sensors/mqtt_rcv.log')
    logger.debug('Finished read_log')
    #sensors = get_home_sensors('../sensors/mqtt_rcv.log')
    sensors = get_latest_sensors(sensor_devs)
    # TODO: should modify the template to take a dict of sensors, but for now ...
    for s in sensors:
        templ_args[s] = sensors[s]
    host,node_port = get_node_addr()
    buttons = make_buttons(exclude=['hourly', 'now'], lon_lat=lon_lat, home_name=home_name, tzoff=tzoff, radar_type=radar_type)  # returns list of HTML string
    buttons = ''.join(buttons)
    logger.debug('call stream_plot')
    time_plot = timeplot.stream_plot(sensor_devs)
    return templ.render(templ_args, img_base64=time_plot, buttons=buttons)

def make_hourly_fcst_page(data_all, heading='Today', hours=[1,2,3,6,9]):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    path = os.path.join(os.path.dirname(__file__), 'templates')
    loader = FileSystemLoader(searchpath=path)
    env = Environment(loader=loader)
    templ_all = env.get_template('wx_hourly_many.html')        # complate page with multiple hours
    all_divs = make_hourly_divs(data_all, hours=hours)
    return templ_all.render(divs=all_divs)

def make_hourly_divs(the_vals, heading='Today', hours=[1,2,3,4], tzoff=-8):
    '''
    Generate a DIV that contains other DIVs for each hour.
    :param the_vals: object of FcstHourlyData
    :param heading:
    :param hours: list of forecast hours from present time
    :return: HTML DIV list
    '''
    path = os.path.join(os.path.dirname(__file__), 'templates')
    loader = FileSystemLoader(searchpath=path)
    env = Environment(loader=loader)
    templ = env.get_template('fcst_hourly_div.html')     # construct a DIV for each hour
    templ_keys = ['temp', 'humidity', 'wind_speed', 'wind_deg', 'weather_description', 'weather_icon', 'pop']
    divs = []
    #tzobj = dt.timezone(dt.timedelta(hours=tz))

    for hour in hours:
        obs = parse_wx_hourly(the_vals, hour, tzoff)
        templ_args = {}
        for key in templ_keys:
            templ_args[key],unitStr = obs.getObsVal(key)
            if key == 'wind_deg':
                templ_args['wind_compass'] = DataParse.wind_compass(templ_args['wind_deg'])
            elif key == 'pop':
                if float(templ_args[key]) < 0.11:
                    templ_args.pop('pop') # remove prob-of-precip so it's not displayed
                else:   # TODO: should handle 'pop' value elsewhere
                    templ_args[key] = '%d' % int(float(templ_args[key]) * 100.0)
            else:
                templ_args[key] = str(templ_args[key])+unitStr
        dt_obs = dt.datetime.fromisoformat(obs.getObsVal('datetime')[0])
        templ_args['time'] = dt_obs.strftime("%a %I %p")
        divs.append(templ.render(templ_args))
    #logger.debug('made {} DIVs'.format(len(divs)))
    #logger.debug('DIV[0]: {}'.format(str(divs[0])))
    return divs

def make_wx_hourly(the_vals, heading='Hourly Forecast'):
    '''
    Generate single hour forecast web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    path = os.path.join(os.path.dirname(__file__), 'templates')
    loader = FileSystemLoader(searchpath=path)
    env = Environment(loader=loader)
    templ = env.get_template('wx_hourly.html')
    templ_keys = ['temp', 'humidity', 'wind_speed', 'wind_deg', 'weather_description', 'weather_icon']

    templ_args = {}
    for key in templ_keys:
        templ_args[key],unit = the_vals.getObsVal(key)
    #templ_args = {key:the_vals.getObsStr(key) for key in templ_keys}
    dt_obs = dt.datetime.fromisoformat(the_vals.getObsVal('datetime')[0])
    # day-of-week name
    day_name = dt_obs.date().strftime('%A')
    templ_args['day_name'] = day_name
    templ_args['time'] = dt_obs.time()
    templ_args['heading'] = heading
    return templ.render(templ_args)

def make_daily_fcst_page(data_all, tzoff=-8, lon_lat=None, home_name='', radar_type=''):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    '''
    tzStr = str(tz)
    if tzStr in myTZ:
        tz_local = myTZ[tzStr].utcoffset()
    '''
    path = os.path.join(os.path.dirname(__file__), 'templates')
    loader = FileSystemLoader(searchpath=path)
    env = Environment(loader=loader)
    templ_all = env.get_template('wx_daily_many.html')  # complete page with multiple days
    templ = env.get_template('fcst_daily_div.html')     # construct a DIV for each day
    templ_keys = ['sunrise', 'sunset', 'temp_max', 'temp_min', 'humidity', 'wind_speed', 'wind_deg', 'weather_description', 'weather_icon', 'pop']
    divs = []
    ndays = len(data_all['daily'])
    ndays = min(ndays,9)

    for day in range(ndays):
        #tzobj = dt.timezone(dt.timedelta(hours=tz)) # inside loop in case ndays crosses daylight hours change
        the_vals = parse_wx_daily(data_all, day, tzoff)
        templ_args = {}
        for key in templ_keys:
            templ_args[key] = the_vals.getObsStr(key)
            #templ_args[key] = metric_to_english(key,templ_args[key])
            if key == 'wind_deg':
                templ_args['wind_compass'] = DataParse.wind_compass(templ_args['wind_deg'])
            elif key == 'pop':  # probability-of-precipitation
                if float(templ_args[key]) < 0.11:
                    templ_args.pop('pop') # remove prob-of-precip so it's not displayed
                else:   # TODO: should handle 'pop' value elsewhere
                    templ_args[key] = '%d' % int(float(templ_args[key]) * 100.0)
        #templ_args = {key:the_vals.getObsStr(key) for key in templ_keys}
        dt_obs = dt.datetime.fromisoformat(the_vals.getObsStr('datetime'))
        # day-of-week name
        day_name = dt_obs.date().strftime('%A')
        templ_args['day_name'] = day_name[:3]
        divs.append(templ.render(templ_args, url_for=url_for))
    host,node_port = get_node_addr()
    buttons = make_buttons(exclude=['hourly', 'daily'], lon_lat=lon_lat, home_name=home_name, tzoff=tzoff, radar_type=radar_type)  # returns list of HTML string
    buttons = ''.join(buttons)
    #logger.debug('make_buttons: {}'.format(buttons))
    #return templ_all.render(divs=divs, node_port=node_port, buttons=buttons, home=home_name)
    return templ_all.render(url_for=url_for, divs=divs, buttons=buttons, home=home_name)

def make_wx_daily(the_vals, heading='Daily'):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    path = os.path.join(os.path.dirname(__file__), 'templates')
    loader = FileSystemLoader(searchpath=path)
    env = Environment(loader=loader)
    templ = env.get_template('wx_daily_one.html')
    templ_keys = ['temp_max', 'temp_min', 'humidity', 'wind_speed', 'wind_deg', 'weather_description', 'weather_icon']

    templ_args = {}
    for key in templ_keys:
        templ_args[key] = the_vals.getObsStr(key)
    #templ_args = {key:the_vals.getObsStr(key) for key in templ_keys}
    dt_obs = dt.datetime.fromisoformat(the_vals.getObsStr('datetime'))
    # day-of-week name
    day_name = dt_obs.date().strftime('%A')
    templ_args['day_name'] = day_name
    #templ_args['time'] = dt_obs.time()
    templ_args['heading'] = heading
    return templ.render(templ_args)

def get_wx_all(lon_lat=None, tz_off=-8):
    '''
    Get data from OpenWeatherMap.
    Request "all" data, but exclude "minutely" data. So we get current obs, all hourly and all daily.
    Request metric data. If US units are desired, conversion is done when generating display.
    :param lon_lat: a tuple or list of (longitude,latitude)
    :return: dict that represents JSON. See OpenWeatherMap API for info.
    '''
    # get OpenWeather data
    if lon_lat:
        lon,lat = lon_lat.split(',')
    else:
        lon = Config.location[0]
        lat = Config.location[1]
    wx_fcst_url = Config.openweatherPrefix + 'onecall?lat={lat}&lon={lon}&appid={API_key}&exclude=minutely&units=metric'.format(
    lat=lat, lon=lon, API_key=ApiKeys.openweather_key)
    request = Request(wx_fcst_url)
    with urlopen(request) as response:
        jdata = response.read()
    data = json.loads(jdata)
    #logger.debug('get_wx_all: json={}, parsed={}'.format(len(jdata), len(data)))
    logger.debug('get_wx_all: return data len={}'.format(len(data)))
    return data

def parse_wx_curr(data, tzoff=-8):
    # Construct the current obs data
    currObs = CurrentObs(data, tzoff)
    logger.debug('parse_wx_curr: return currObs')
    return currObs

def parse_wx_daily(data, iday=1, tzoff=-8):
    # Construct the current obs data
    currObs = FcstDailyData(data, iday, tzoff)
    return currObs

def parse_wx_hourly(data, ihour=1, tzoff=-8):
    if False:
        # I put this here when OpenWeather messed up and started delivering hourly forecasts for every 6 hours instead
        hr_recs = data['hourly']
        for rec in hr_recs:
            logger.debug('hourly: dt={}'.format(dt.datetime.fromtimestamp(rec['dt'])))
    # Construct the current obs data
    currObs = FcstHourlyData(data, ihour, tzoff)
    return currObs

if __name__ == '__main__':
    # This is only run when testing
    # get OpenWeather data
    wx_fcst_url = Config.openweatherPrefix + 'onecall?lat={lat}&lon={lon}&appid={API_key}&exclude=minutely&units=metric'.format(
        lat=Config.location[1], lon=Config.location[0], API_key=ApiKeys.openweather_key)
    request = Request(wx_fcst_url)
    with urlopen(request) as response:
        jdata = response.read()
    #print(jdata)
    data = json.loads(jdata)
    
    # Construct the current obs data
    currObs = CurrentObs(data)
    # display it
    print('CurrentObs')
    for key in currObs.obs:
        print('key={}, value={}'.format(key,currObs.getObsStr(key)))
        
    print('Number of daily forecasts = {}'.format(len(data['daily'])))
    iday = 0
    daily = FcstDailyData(data,iday)
    print('Daily {}'.format(iday))
    for key in daily.obs:
        print('key={}, value={}'.format(key,daily.getObsStr(key)))
        
    print('Number of hourly forecasts = {}'.format(len(data['hourly'])))
    iday = 0
    hourly = FcstHourlyData(data,iday)
    print('Hourly {}'.format(iday))
    for key in hourly.obs:
        print('key={}, value={}'.format(key,hourly.getObsStr(key)))

    make_html(currObs)
