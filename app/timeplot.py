# create graphs of sensor values
# 2023-01-04: now uses files that contain JSON for input, no more custom format.
#   Input log file has JSON on each row, representing time-stamped data from a sensor.
# When run as main, it displays a plot made by matplotlib.
# When imported and called from a Flask process it generates a plot as HTTP stream.
import io
import datetime as dt
import matplotlib.pyplot as plt
import base64
from sensor_in import log_parse, log_parse_json, sensor_devs, SENSOR_NAMES
import logging
import my_logger
logger = my_logger.setup_logger(__name__, '../ow.log', level=logging.DEBUG)

def calc_scale(vals, interval=10):
    '''
    Calculate Y min/max for a nice plot.
    Interval is minimum scale of Y axis.
    Actual interval must fit the min/max vals and must be multiple of interval.
    :param vals:
    :param interval:
    :return: ymin,ymax
    '''
    y0 = min(vals)
    y1 = max(vals)
    ylen = y1 - y0
    '''
    Examples:
    ylen=8, interval=10, n_interval=1
    ylen=27, interval=10, n_interval=3
    ylen=12, interval=5, n_interval=3
    '''
    n_interval = int((ylen + interval) / interval)  # number of tick marks?
    # TODO: try to round minimum to nearest interval multiple
    limits = int(y0),int(y0)+n_interval*interval
    logger.debug('calc_scale: vals= {},{}. scale= {}, {}'.format(y0,y1,limits[0],limits[1]))
    return limits

def make_plot(sensor_devs, sys_name='gn-pi-zero-2'):
    '''
    Plot sensor readings for the current day
    :param logfile: daily file of readings from devices
    :param sys_name: default is my outdoor Pi. If value is None, plot all devices found
    :return:
    '''
    #global sensor_devs  # SensorVals object for each computer-sensor
    #read_log(logfile)   # fill the sensor_devs values
    #plt.figure(dpi=100.0, figsize=(6,4))
    axnum = {'temp_c': 0, 'humidity': 1, 'pressure': 2, 'pm25': 3}
    fig,axs = plt.subplots(len(axnum))
    yaxlim = {} # if there are multiple devices on one plot, then limits are the min/max required by all
    dev_keys = sorted(sensor_devs.keys())   # these will be MQTT topic names
    logger.debug('dev_keys:sorted = {}'.format(dev_keys))
    for dev_key in dev_keys:
        # TODO: should I strip optional "/J" from end of dev_keys?
        location,computer,sensor,_ = dev_key.split('/')
        legend_label = computer[-6:]    # names such as "gn-pi-zero-1"
        if sys_name and sys_name.find(computer) == -1:
            continue    # don't plot this data
        dev = sensor_devs[dev_key]
        logger.debug('device = {}'.format(dev.name))
        for key in dev.vals:
            # dev.vals is a dict that holds lists of values from each sensor, e.g., 'temp_c' and 'pressure'
            logger.debug('  key={} has {} values'.format(key,len(dev.vals[key])))
        if dev_key.find('bme280') >= 0 or dev_key.find('pm25') >= 0:
            vtimes = [dt.datetime.fromisoformat(t) for t in dev.vals['time']]
            if dev_key.find('bme280') >= 0:
                # TODO: should have common method for each of the graphs, rather than repeat code
                senskey = 'temp_c'
                iplt = axnum[senskey]
                vals = dev.vals[senskey]
                vals = [val*1.8+32.0 for val in vals]   # TODO: should have selector for C or F
                y0,y1 = calc_scale(vals, interval=5)
                if senskey in yaxlim:
                    # more than one plot for this senskey
                    yaxlim[senskey] = (min(yaxlim[senskey][0],y0), max(yaxlim[senskey][1],y1))
                else:
                    yaxlim[senskey] = (y0,y1)   # first time for this senskey
                axs[iplt].yaxis.set_major_locator(plt.MaxNLocator(5))
                axs[iplt].set_ylim(ymin=yaxlim[senskey][0], ymax=yaxlim[senskey][1])
                axs[iplt].plot(vtimes, vals, label=legend_label)
                axs[iplt].set_title('Temp F', y=1.0, pad=-14)
                ########
                senskey = 'humidity'
                iplt = axnum[senskey]
                vals = dev.vals[senskey]
                y0,y1 = calc_scale(vals, interval=10)
                if senskey in yaxlim:
                    yaxlim[senskey] = (min(yaxlim[senskey][0],y0), max(yaxlim[senskey][1],y1))
                else:
                    yaxlim[senskey] = (y0,y1)
                axs[iplt].yaxis.set_major_locator(plt.MaxNLocator(4))
                axs[iplt].set_ylim(ymin=yaxlim[senskey][0], ymax=yaxlim[senskey][1])
                axs[iplt].plot(vtimes, vals, label=legend_label)
                axs[iplt].set_title('Humidity', y=1.0, pad=-14)
                ########
                senskey = 'pressure'
                iplt = axnum[senskey]
                vals = dev.vals[senskey]
                y0,y1 = calc_scale(vals, interval=2)
                if senskey in yaxlim:
                    yaxlim[senskey] = (min(yaxlim[senskey][0],y0), max(yaxlim[senskey][1],y1))
                else:
                    yaxlim[senskey] = (y0,y1)
                axs[iplt].yaxis.set_major_locator(plt.MaxNLocator(4))
                axs[iplt].set_ylim(ymin=yaxlim[senskey][0], ymax=yaxlim[senskey][1])
                axs[iplt].plot(vtimes, vals, label=legend_label)
                axs[iplt].set_title('Pressure', y=1.0, pad=-14)
            if dev_key.find('pm25') >= 0:
                # TODO: used to be PM2_5
                #senskey = 'PM2_5'
                senskey = 'pm25'
                iplt = axnum[senskey]
                vals = [int(v) for v in dev.vals[senskey]]
                y0,y1 = calc_scale(vals, interval=10)
                if senskey in yaxlim:
                    yaxlim[senskey] = (min(yaxlim[senskey][0],y0), max(yaxlim[senskey][1],y1))
                else:
                    yaxlim[senskey] = (y0,y1)
                axs[iplt].yaxis.set_major_locator(plt.MaxNLocator(4))
                axs[iplt].set_ylim(ymin=yaxlim[senskey][0], ymax=yaxlim[senskey][1])
                axs[iplt].plot(vtimes, vals, label=legend_label)
                axs[iplt].set_title('Air Quality 2.5', y=1.0, pad=-14)
    plt.gcf().autofmt_xdate()
    axs[0].legend(loc="upper left")
    return fig,axs

def stream_plot(sensor_devs):
    '''
    Called when package is used for HTML display.
    :param logfile:
    :return:
    '''
    #global sensor_devs
    logger.debug('stream_plot: start')
    fig,axs = make_plot(sensor_devs, sys_name=None)
    # this technique from https://stackoverflow.com/questions/14824522/dynamically-serving-a-matplotlib-image-to-the-web-using-python
    # it stuffs base64 encoded image into HTML IMG tag.
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
    buf.close()
    #return send_file(img_base64, mimetype='image/png')
    sensor_devs = {}    # in Flask must delete sensor_devs after each plot
    return img_base64

def main(logfile, system='gn-pi-zero-1'):
    '''
    Called when testing and running this program standalone.
    :param logfile:
    :param system:
    :return:
    '''
    make_plot(logfile, sys_name=system)
    '''
    # this technique from https://stackoverflow.com/questions/14824522/dynamically-serving-a-matplotlib-image-to-the-web-using-python
    # it stuffs base64 encoded image into HTML IMG tag.
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
    buf.close()
    logger.debug('data: image/png;base64,')
    # and then print img_base64 into HTTP stream
    # or Flask can do this:
    return send_file(buf, mimetype='image/png')
    # or use this in the Jinja2 template:
     <img id="picture" src="data:image/jpeg;base64,{{ img_base64 }}">
    '''
    plt.show()
    # TODO: save image and then send to HTTP stream
    '''
    #response = 'HTTP/1.1 200 OK\n\n'
    print('Content-type: image/png\n')
    sys.stdout.write(load_binary(img_file))
    sys.stdout.flush()
    '''

if __name__ == '__main__':
    logfile = '../sensors/mqtt_rcv.log'
    #logfile = 'tsunami.2022-01-15.log'
    main(logfile, 'gn-pi-zero-2')
