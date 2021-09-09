# create graphs of sensor values
import sys
import io
import datetime as dt
import matplotlib
import matplotlib.pyplot as plt
from flask import send_file
import base64
import logging
import my_logger
logger = my_logger.setup_logger(__name__,'ow.log', level=logging.DEBUG)

# there are more sensor values, but these are the ones we want
SENSOR_NAMES = ['time', 'PM2_5', 'temp_c', 'humidity', 'pressure']
sensor_devs = {}

class SensorVals:
    def __init__(self,sens_name):
        self.name = sens_name
        self.vals = {}
    def add_value(self, val_name, value):
        if not val_name in self.vals:
            self.vals[val_name] = list()
        self.vals[val_name].append(value)

def log_parse(line):
    global sensor_devs
    values = {}
    l = line.split(':',maxsplit=1)
    #fld1 = line.find(':')
    #sens_dev = line[:fld1].strip()
    sens_dev = l[0].strip()
    if not sens_dev in sensor_devs:
        sensor_devs[sens_dev] = SensorVals(sens_dev)
        location,computer,sensor = sens_dev.split('/')
        logger.debug('{},{},{}'.format(location,computer,sensor))
    #ll = line[fld1+1:].strip()
    ll = l[1].strip()
    ff = ll.split(',')
    for f in ff:
        fld_name,fld_val = f.split('=')
        #values[fld_name] = fld_val
        if fld_name == 'time':
            val = fld_val
        else:
            val = float(fld_val)
        sensor_devs[sens_dev].add_value(fld_name,val)

def read_log(fname):
    with open(fname, 'r') as df:
        lines = df.readlines()
    for line in lines:
        log_parse(line)

def load_binary(filename):
    with open(filename, 'rb') as file_handle:
        return file_handle.read()

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
    n_interval = int((ylen + interval) / interval)
    # TODO: try to round minimum to nearest interval multiple
    limits = int(min(vals)),int(min(vals))+n_interval*interval
    logger.debug('calc_scale: vals= {},{}. scale= {}, {}'.format(y0,y1,limits[0],limits[1]))
    return limits

def make_plot(logfile, sys_name='gn-pi-zero-1'):
    '''
    Plot sensor readings for the current day
    :param logfile: daily file of readings from devices
    :param sys_name: default is my outdoor Pi. If value is None, plot all devices found
    :return:
    '''
    global sensor_devs  # SensorVals object for each computer-sensor
    read_log(logfile)
    # now sensor_devs should be filled
    plt.figure(dpi=100.0, figsize=(6,4))
    fig,axs = plt.subplots(3)
    #iplt = 0
    axnum = {'temp_c': 0, 'humidity': 1, 'PM2_5': 2}
    yaxlim = {} # limits accumulated if there are multiple devices on one plot
    dev_keys = sorted(sensor_devs.keys())
    logger.debug('dev_keys:sorted = {}'.format(dev_keys))
    for dev_key in dev_keys:
        location,computer,sensor = dev_key.split('/')
        legend_label = computer[-6:]
        if sys_name and sys_name.find(computer) == -1:
            continue    # don't plot this data
        dev = sensor_devs[dev_key]
        logger.debug('device = {}'.format(dev.name))
        for key in dev.vals:
            logger.debug('  key={} has {} values'.format(key,len(dev.vals[key])))
        if dev_key.find('bme280') >= 0 or dev_key.find('pm25') >= 0:
            vtimes = [dt.datetime.fromisoformat(t) for t in dev.vals['time']]
            if dev_key.find('bme280') >= 0:
                senskey = 'temp_c'
                iplt = axnum[senskey]
                vals = dev.vals[senskey]
                vals = [val*1.8+32.0 for val in vals]
                y0,y1 = calc_scale(vals, interval=5)
                if senskey in yaxlim:
                    yaxlim[senskey] = (min(yaxlim[senskey][0],y0), max(yaxlim[senskey][1],y1))
                else:
                    yaxlim[senskey] = (y0,y1)
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
            if dev_key.find('pm25') >= 0:
                senskey = 'PM2_5'
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
    axs[0].legend(loc="upper right")
    return fig,axs

def stream_plot(logfile='../sensors/mqtt_rcv.log'):
    global sensor_devs
    logger.debug('stream_plot: start')
    fig,axs = make_plot(logfile, sys_name=None)
    # this technique from https://stackoverflow.com/questions/14824522/dynamically-serving-a-matplotlib-image-to-the-web-using-python
    # it stuffs base64 encoded image into HTML IMG tag.
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8').replace('\n', '')
    buf.close()
    #return send_file(img_base64, mimetype='image/png')
    sensor_devs = {}    # in Flask must delete sensor_devs after each plot
    return img_base64

def main(logfile):
    make_plot(logfile)
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
    main(logfile)
