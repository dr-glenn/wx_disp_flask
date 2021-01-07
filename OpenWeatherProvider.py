# -*- coding: utf-8 -*-                 # NOQA
# OpenWeather data provider.
# It returns current forecast for the next week
# This page describes the values returned: https://darksky.net/dev/docs#api-request-types
# Or just look at this page for an example: https://darksky.net/dev/docs

import urllib
from urllib.request import urlopen,Request
import json
import datetime as dt
import Config
import ApiKeys
import logging
import my_logger
from jinja2 import Template,Environment,PackageLoader,select_autoescape,FileSystemLoader

logger = my_logger.setup_logger(__name__,'ow.log', level=logging.DEBUG)
CURRENT_INTERVAL = 0
HOURLY_INTERVAL = 1
DAILY_INTERVAL =2
# units for values: temperature, wind
METRIC=0
US=1

def c_to_f(temp):
    return 1.8 * temp + 32.0
'''
OpenWeather defines some strings to describe weather icons,
See page for more info: https://openweathermap.org/weather-conditions#Weather-Condition-Codes-2
In the 'weather' entry a text description is returned as well as 'icon' name.
The same icon may be used for variations on the conditions, e.g., "light rain" and "very heavy rain"
have same icon - so you need to display the text also.
And there are day and night icons: same numeric code for icon, with suffix 'd' or 'n'.
'''
# Here is a list of names, with mapping to icons stored locally
icon_names = {
'clear-day':            'clear.png',
'clear-night':          'n_clear.png',
'rain':                 'rain.png',
'snow':                 'snow.png',
'sleet':                'sleet.png',
'wind':                 '',
'fog':                  'fog.png',
'cloudy':               'cloudy.png',
'partly-cloudy-day':    'partlycloudy.png',
'partly-cloudy-night':  'n_partlycloudy.png',
}

dt_keys = ('dt', 'sunrise', 'sunset')

class WxData:
    def __init__(self):
        self.wxdata = None
        self.wxurl = Config.darkPrefix + ApiKeys.darksky_key
        self.wxurl += '/' + str(Config.primary_coordinates[0]) + ',' + str(Config.primary_coordinates[1])
        self.wxurl += '?exclude=minutely&units=us'
        logger.debug('wxurl='+self.wxurl)
        self.hasData = False
    def getwx(self):
        self.hasData = False
        if False:
            r = QUrl(self.wxurl)
            r = QNetworkRequest(r)
            self.manager = QtNetwork.QNetworkAccessManager()
            self.wxreply = self.manager.get(r)
            self.wxreply.finished.connect(self.wxfinished)
        else:
            self.wxreply = urllib.request.urlopen(self.wxurl)
            wxstr = self.wxreply.read()
            logger.debug('wxstr: %s' %(wxstr[:200]))
            self.wxdata = json.loads(wxstr)
            self.hasData = True
    def wxfinished(self):
        wxstr = str(self.wxreply.readAll())
        if not wxstr:
            logger.warning('wxstr is None')
            return
        self.wxdata = json.loads(wxstr)
        self.hasData = True
    def getData(self):
        if self.hasData:
            return self.wxdata
        else:
            return None
        
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
    def __init__(self,wxdata,dataKeys,daily=False):
        self.daily = daily
        self.obs = {}
        for key in dataKeys:
            if isinstance(key[1],(list,tuple)):
                try:
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
                        data = dt.datetime.fromtimestamp(data)
                    logger.debug('key=%s, data=%s' %(key[1],str(data)))
                else:
                    # DarkSky has optional fields, so it's OK if key[1] not found
                    logger.info('DataParse: key=%s not present in wxdata' %(key[1]))
                    continue
            if key[2] == -1 or key[2] == Config.metric:
                # Config.metric has value of either 0 or 1
                self.obs[key[0]] = [data,key[3]]
                logger.debug('save obs: key=%s, value=%s' %(key[0],str(self.obs[key[0]])))
            else:
                # key[2] != Config.metric, so skip this obs
                pass
                
        # Special case for 'icon', because we have local copies
        """
        #iconurl = wxdata['icon_url']
        if wxdata['icon'] in icon_names:
            icon_png = icon_names[wxdata['icon']]
            self.obs['icon'] = [Config.icons + "/" + icon_png,'']
        """
                
    def getObsStr(self,key, units=METRIC):
        # Get value from wxdata + the appropriate units string
        if key in self.obs:
            # TODO: the obs tables should have a conversion function
            try:
                obsVal = float(self.obs[key][0])
                if abs(obsVal) >= 10.0:
                    obsVal = int(obsVal + 0.5)  # get rid of decimal places
                else:
                    obsVal = float('%.1f' %(obsVal))
            except:
                # could not convert to float, so assume it's a string
                obsVal = self.obs[key][0]
            retval = str(obsVal) + self.obs[key][1]
            return retval
        else:
            logger.warning('key=%s not found' %(key))
            return None

    def getObsVal(self, key, units=METRIC):
        # Get value from wxdata + the appropriate units string
        if key in self.obs:
            # TODO: the obs tables should have a conversion function
            try:
                obsVal = float(self.obs[key][0])
                if units==US:
                    if key=='wind_speed' or key=='wind_gust':
                        obsVal = 2.237 * obsVal # m/s to miles/hour
                    elif key.startswith('temp') or key.startswith('feels_like'):
                        obsVal = c_to_f(obsVal)
                if abs(obsVal) >= 10.0:
                    obsVal = int(obsVal + 0.5)  # get rid of decimal places
                else:
                    obsVal = float('%.1f' % (obsVal))
            except:
                # could not convert to float, so assume it's a string
                obsVal = self.obs[key][0]
            #retval = str(obsVal) + self.obs[key][1]
            retval = str(obsVal)
            return retval
        else:
            logger.warning('key=%s not found' % (key))
            return None

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
    obsKeys = [
        # app key,              data key,               metric, units
        ('datetime',  'dt',   -1, ''),
        ('sunrise', 'sunrise', -1, ''),
        ('sunset', 'sunset', -1, ''),
        ('temp', 'temp', 1, u'°C'),
        ('feels_like', 'feels_like', 1, u'°C'),
        ('pressure', 'pressure', 1, ' mb'),
        ('humidity', 'humidity', -1, '%'),
        ('dew_point', 'dew_point', 1, u'°C'),
        ('cloud_cover', 'clouds', -1, '%'),
        ('uv_index', 'uvi', -1, ''),
        ('visibility', 'visibility', -1, ' m'),
        ('wind_speed', 'wind_speed', 1, ' m/s'),
        ('wind_gust', 'wind_gust', 1, ' m/s'),
        ('wind_deg', 'wind_deg', -1, ''),
        #('rain', 'rain', 1, ' mm'),
        ('rain_1h', '(rain,1h)', 1, ' mm'),
        #('snow', 'snow', 1, ' mm'),
        ('snow_1h', '(snow,1h)', 1, ' mm'),
        ('weather_id', ('weather','id'), -1, ''),   # integer
        ('weather_main', ('weather','main'), -1, ''),   # category, such as Rain, Snow
        ('weather_description', ('weather','description'), -1, ''), # text
        ('weather_icon', ('weather','icon'), -1, ''),   # name of icon to fetch
    ]
    # other keys: precipProbability, precipType, dewPoint, cloudCover, uvIndex, visibility, ozone
    def __init__(self,wxdata):
        print(wxdata['current'])
        DataParse.__init__(self,wxdata['current'],self.obsKeys,daily=False)

class FcstDailyData(DataParse):
    # Lookup table for key used in application display,
    # key used in wxdata returned by wunderground,
    # metric=1 or English=0 units,
    # and displays units (if any) in the application
    # NOTE: must use 'daily/data' node to fetch these
    obsKeys = [
        # app key,  data key,   metric, units
        ('datetime', 'dt', -1, ''),
        ('sunrise', 'sunrise', -1, ''),
        ('sunset', 'sunset', -1, ''),
        ('temp_day', ('temp','day'), 1, u'°C'),
        ('temp_min', ('temp','min'), 1, u'°C'),
        ('temp_max', ('temp','max'), 1, u'°C'),
        ('temp_night', ('temp','night'), 1, u'°C'),
        ('temp_eve', ('temp','eve'), 1, u'°C'),
        ('temp_morn', ('temp','morn'), 1, u'°C'),
        ('feels_like_day', ('feels_like','day'), 1, u'°C'),
        ('feels_like_night', ('feels_like','night'), 1, u'°C'),
        ('feels_like_eve', ('feels_like','eve'), 1, u'°C'),
        ('feels_like_morn', ('feels_like','morn'), 1, u'°C'),
        ('pressure', 'pressure', 1, ' mb'),
        ('humidity', 'humidity', -1, '%'),
        ('dew_point', 'dew_point', 1, u'°C'),
        ('wind_speed', 'wind_speed', 1, ' m/s'),
        ('wind_deg', 'wind_deg', -1, ''),
        ('weather_id', ('weather','id'), -1, ''),   # integer
        ('weather_main', ('weather','main'), -1, ''),   # category, such as Rain, Snow
        ('weather_description', ('weather','description'), -1, ''), # text
        ('weather_icon', ('weather','icon'), -1, ''),   # name of icon to fetch
        ('cloud_cover', 'clouds', -1, '%'),
        ('uv_index', 'uvi', -1, ''),
        ('pop', 'pop', -1, '%'),
    ]
    # other keys: sunriseTime, sunsetTime, moonPhase, precipIntensityMax, precipIntensityMaxTime, more
    def __init__(self,wxdata,iday):
        print(wxdata['daily'][iday])
        DataParse.__init__(self,wxdata['daily'][iday],self.obsKeys,daily=True)

class FcstHourlyData(DataParse):
    # Lookup table for key used in application display,
    # key used in wxdata returned by wunderground,
    # metric=1 or English=0 units,
    # and displays units (if any) in the application
    # NOTE: must use 'hourly/data' node to fetch these
    obsKeys = [
        # app key,  data key,   metric, units
        ('datetime', 'dt', -1, ''),
        ('temp', 'temp', 1, u'°C'),
        ('feels_like', 'feels_like', 1, u'°C'),
        ('pressure', 'pressure', 1, ' mb'),
        ('humidity', 'humidity', -1, '%'),
        ('dew_point', 'dew_point', 1, u'°C'),
        ('wind_speed', 'wind_speed', 1, ' m/s'),
        ('wind_deg', 'wind_deg', -1, ''),
        ('weather_id', ('weather','id'), -1, ''),   # integer
        ('weather_main', ('weather','main'), -1, ''),   # category, such as Rain, Snow
        ('weather_description', ('weather','description'), -1, ''), # text
        ('weather_icon', ('weather','icon'), -1, ''),   # name of icon to fetch
        ('cloud_cover', 'clouds', -1, '%'),
        ('uv_index', 'uvi', -1, ''),
        ('pop', 'pop', -1, '%'),
    ]
    # other keys: apparentTemperature, dewPoint, humidity, pressure, windSpeed, windGust, windBearing, cloudCover, uvIndex, visibility, ozone
    def __init__(self,wxdata,ihour):
        DataParse.__init__(self,wxdata['hourly'][ihour],self.obsKeys,daily=False)

def make_html(the_vals, heading='Current'):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    loader = FileSystemLoader('./templates')
    env = Environment(loader=loader)
    templ = env.get_template('wx_curr.html')
    templ_args = {}
    #templ_args['obs'] = obs
    templ_vals = [[key,the_vals.getObsStr(key)] for key in the_vals.obs]
    #print(str(templ_vals))
    #print(templ.render(obs=templ_vals))
    return templ.render(heading=heading, obs=templ_vals)

def make_wx_1(the_vals, heading='Current', interval=CURRENT_INTERVAL):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    loader = FileSystemLoader('./templates')
    env = Environment(loader=loader)
    templ = env.get_template('wx_1.html')
    templ_keys = ['temp', 'humidity', 'wind_speed', 'wind_deg', 'weather_description', 'weather_icon']

    templ_args = {}
    for key in templ_keys:
        templ_args[key] = the_vals.getObsStr(key)
    #templ_args = {key:the_vals.getObsStr(key) for key in templ_keys}
    dt_obs = dt.datetime.fromisoformat(the_vals.getObsStr('datetime'))
    # day-of-week name
    day_name = dt_obs.date().strftime('%A')
    if interval == DAILY_INTERVAL:
        templ_args['date'] = day_name
        #templ_args['time'] = dt_obs.time()
    else:
        templ_args['date'] = dt_obs.date()
        templ_args['time'] = dt_obs.time()
    templ_args['heading'] = heading
    return templ.render(templ_args)

def make_wx_current(the_vals, heading='Current Obs', interval=CURRENT_INTERVAL):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    loader = FileSystemLoader('./templates')
    env = Environment(loader=loader)
    templ = env.get_template('wx_current.html')
    templ_keys = ['temp', 'humidity', 'feels_like', 'wind_speed', 'wind_deg', 'weather_description', 'weather_icon']

    templ_args = {}
    for key in templ_keys:
        templ_args[key] = the_vals.getObsVal(key,units=US)
        if key == 'wind_deg':
            templ_args['wind_compass'] = DataParse.wind_compass(templ_args['wind_deg'])
    #templ_args = {key:the_vals.getObsStr(key) for key in templ_keys}
    dt_obs = dt.datetime.fromisoformat(the_vals.getObsStr('datetime'))
    # day-of-week name
    day_name = dt_obs.date().strftime('%A')
    templ_args['day_name'] = day_name
    templ_args['time'] = dt_obs.strftime('%I:%M %p')
    dt_sunrise = dt.datetime.fromisoformat(the_vals.getObsStr('sunrise'))
    dt_sunset = dt.datetime.fromisoformat(the_vals.getObsStr('sunset'))
    templ_args['sunrise'] = dt_sunrise.strftime('%H:%M')
    templ_args['sunset'] = dt_sunset.strftime('%H:%M')
    templ_args['heading'] = heading
    return templ.render(templ_args)

def make_wx_hourly(the_vals, heading='Hourly Forecast', interval=HOURLY_INTERVAL):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    loader = FileSystemLoader('./templates')
    env = Environment(loader=loader)
    templ = env.get_template('wx_hourly.html')
    templ_keys = ['temp', 'humidity', 'wind_speed', 'wind_deg', 'weather_description', 'weather_icon']

    templ_args = {}
    for key in templ_keys:
        templ_args[key] = the_vals.getObsStr(key)
    #templ_args = {key:the_vals.getObsStr(key) for key in templ_keys}
    dt_obs = dt.datetime.fromisoformat(the_vals.getObsStr('datetime'))
    # day-of-week name
    day_name = dt_obs.date().strftime('%A')
    templ_args['day_name'] = day_name
    templ_args['time'] = dt_obs.time()
    templ_args['heading'] = heading
    return templ.render(templ_args)

def make_wx_daily(the_vals, heading='Current', interval=DAILY_INTERVAL):
    '''
    Generate web page with jinja2.
    :param obs: object of CurrentObs, FcstDailyData, or FcstHourlyData
    :return:
    '''
    loader = FileSystemLoader('./templates')
    env = Environment(loader=loader)
    templ = env.get_template('wx_daily.html')
    templ_keys = ['temp_max', 'temp_min', 'humidity', 'wind_speed', 'wind_deg', 'weather_description', 'weather_icon']

    templ_args = {}
    for key in templ_keys:
        templ_args[key] = the_vals.getObsStr(key)
    #templ_args = {key:the_vals.getObsStr(key) for key in templ_keys}
    dt_obs = dt.datetime.fromisoformat(the_vals.getObsStr('datetime'))
    # day-of-week name
    day_name = dt_obs.date().strftime('%A')
    if interval == DAILY_INTERVAL:
        templ_args['day_name'] = day_name
        #templ_args['time'] = dt_obs.time()
    else:
        templ_args['date'] = dt_obs.date()
        templ_args['time'] = dt_obs.time()
    templ_args['heading'] = heading
    return templ.render(templ_args)

def get_wx_all():
    # get OpenWeather data
    wx_fcst_url = 'https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&appid={API_key}&exclude=minutely&units=metric'.format(
    lat=Config.location[1], lon=Config.location[0], API_key=ApiKeys.openweather_key)
    request = Request(wx_fcst_url)
    with urlopen(request) as response:
        jdata = response.read()
    #print(jdata)
    data = json.loads(jdata)
    return data

def parse_wx_curr(data):
    # Construct the current obs data
    currObs = CurrentObs(data)
    return currObs

def parse_wx_daily(data, iday=1):
    # Construct the current obs data
    currObs = FcstDailyData(data, iday)
    return currObs

def parse_wx_hourly(data, ihour=1):
    # Construct the current obs data
    currObs = FcstHourlyData(data, ihour)
    return currObs

if __name__ == '__main__':
    # get OpenWeather data
    wx_fcst_url = 'https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&appid={API_key}&exclude=minutely&units=metric'.format(
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