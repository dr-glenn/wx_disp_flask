from flask import Flask, make_response, request, current_app
from functools import update_wrapper
from datetime import timedelta
import OpenWeatherProvider as ow
import radar_disp as radar
import logging
import my_logger
logger = my_logger.setup_logger(__name__,'ow.log', level=logging.DEBUG)

app = Flask(__name__,static_folder='static')

# got this CORS solution from https://stackoverflow.com/questions/26980713/solve-cross-origin-resource-sharing-with-flask
def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, str):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, str):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers
            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/now')
def wx_show_current():
    # TODO: want to know value of the route
    route = 'now'
    wxdata = ow.get_wx_all()
    obs = ow.parse_wx_curr(wxdata)
    html = ow.make_wx_current(obs, heading='Current Weather')
    return html

@app.route('/all_now')
def wx_show_all_current():
    wxdata = ow.get_wx_all()
    obs = ow.parse_wx_curr(wxdata)
    hourly = ow.parse_wx_hourly(wxdata,12)
    daily = ow.parse_wx_daily(wxdata,1)
    html = ow.make_html(obs, hourly, daily, heading='Current Observations')
    return html

@app.route('/one_day')
def wx_show_daily():
    wxdata = ow.get_wx_all()
    obs = ow.parse_wx_daily(wxdata) # use default day value
    #html = ow.make_html(obs, heading='Daily Forecast')
    html = ow.make_wx_daily(obs, heading='Daily Forecast', interval=ow.DAILY_INTERVAL)
    return html

@app.route('/one_hour')
def wx_show_hour():
    wxdata = ow.get_wx_all()
    obs = ow.parse_wx_hourly(wxdata)    # use default hour value
    html = ow.make_wx_hourly(obs, heading='Hourly Forecast')
    return html

# display a page of multiple hourly forecasts
@app.route('/hourly')
def wx_show_hourly():
    wxdata = ow.get_wx_all()
    #obs = ow.parse_wx_hourly(wxdata)
    html = ow.make_hourly_fcst_page(wxdata, heading='Hourly Forecast')
    return html

# return HTML for multiple hourly forecasts. Typically an AJAX call to insert content into page.
# This route is used by another web app on a different port, so crossdomain is needed.
@app.route('/hourly_divs')
@crossdomain(origin='*')
def get_hourly_divs():
    lon_lat = request.args.get('lon_lat')   # None if param not in request
    hoursStr = request.args.get('hours')
    tzOffset = request.args.get('tz')
    if tzOffset:
        tzOffset = int(tzOffset)
    else:
        tzOffset = -8
    if hoursStr:
        hours = [int(h) for h in hoursStr.split(',')]
    else:
        hours = [1,2,3]
    logger.debug('get_hourly_divs, lon_lat={}, hours={}'.format(lon_lat,hours))
    wxdata = ow.get_wx_all(lon_lat)
    divs = ow.make_hourly_divs(wxdata, hours=hours, tzoff=tzOffset)
    return '<br>\n'.join(divs)

@app.route('/daily')
def wx_show_all_daily():
    lon_lat = request.args.get('lon_lat')   # None if param not in request
    #tz_off = request.args.get('tz_off')     # time zone offset in hours
    tzOffset = request.args.get('tz')
    homeName = request.args.get('home_name')
    if tzOffset:
        tzOffset = int(tzOffset)
    else:
        tzOffset = -8
    wxdata = ow.get_wx_all(lon_lat, tzOffset)
    html = ow.make_daily_fcst_page(wxdata, tzOffset, homeName)
    return html

# example of a radar display that I will never make operational
@app.route('/radar')
def radar_show():
    return radar.get_html()

if __name__ == '__main__':
    app.run(host='0.0.0.0')
