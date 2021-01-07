from flask import Flask, url_for
import OpenWeatherProvider as ow
import radar_disp as radar

app = Flask(__name__,static_folder='static')


@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/curr')
def wx_show_current():
    wxdata = ow.get_wx_all()
    obs = ow.parse_wx_curr(wxdata)
    html = ow.make_wx_current(obs, heading='Current Weather')
    return html

@app.route('/all_curr')
def wx_show_all_current():
    wxdata = ow.get_wx_all()
    obs = ow.parse_wx_curr(wxdata)
    html = ow.make_html(obs, heading='Current Observations')
    return html

@app.route('/daily')
def wx_show_daily():
    wxdata = ow.get_wx_all()
    obs = ow.parse_wx_daily(wxdata)
    #html = ow.make_html(obs, heading='Daily Forecast')
    html = ow.make_wx_daily(obs, heading='Daily Forecast', interval=ow.DAILY_INTERVAL)
    return html

@app.route('/hourly')
def wx_show_hourly():
    wxdata = ow.get_wx_all()
    obs = ow.parse_wx_hourly(wxdata)
    html = ow.make_wx_hourly(obs, heading='Hourly Forecast')
    return html

@app.route('/radar')
def radar_show():
    return radar.get_html()
if __name__ == '__main__':
    app.run()
