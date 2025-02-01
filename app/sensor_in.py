import json
import logging
import my_logger
logger = my_logger.setup_logger(__name__, '../ow.log', level=logging.DEBUG)

# values found in the MQTT JSON messages
# there are more sensor values, but these are the ones we want
SENSOR_NAMES = ['time', 'pm25', 'temp_c', 'humidity', 'pressure']

sensor_devs = {}    # collection of SensorVals indexed by MQTT topic name

class SensorVals:
    '''
    A Sensor can have multiple devices within, such as BME280 that measures temp, pressure, humidity.
    Member "vals" is a dict of all devices and the key values are a list.
    Example: get a list of temperatures from a BME280. temps = bme_dev.vals['temp_c']. To use
    the temp_c values, you should pair them with bme_dev.vals['time'], just in case they were not
    stored in time sequence.
    '''
    def __init__(self,sens_name):
        self.name = sens_name
        self.vals = {}
    def add_value(self, val_name, value):
        '''
        Values are presumed to be added in chronological order, if not, we could use 'time' to
        fix up the final list of values.
        :param val_name: such as 'temp_c', 'humidity', 'pm25', 'time'
        :param value:
        :return:
        '''
        if not val_name in self.vals:
            self.vals[val_name] = list()
        self.vals[val_name].append(value)

def log_parse(line):
    global sensor_devs
    """
    These are the log lines. It would be better if this was JSON
    gn_home/gn-pi-zero-2/pm25: time=2022-11-06T00:55:54,PM1_0=3,PM2_5=3,PM10_0=4
    gn_home/gn-pi-zero-2/bme280: time=2022-11-06T01:00:54,temp_c=16.8,humidity=60.5,pressure=1011.1
    """
    values = {}
    l = line.split(':',maxsplit=1)
    logger.debug('log_parse: l={}'.format(line))
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

def log_parse_json(line):
    global sensor_devs
    """
    Parse each message line. Contents will include 'topic', 'time', and any number of sensor names and values.
    These are the JSON log lines.
    {"time": "2023-01-03T12:10:10", "temp_c": "15.4", "temp_f": "59.7", "humidity": "66.7", "pressure": "1012.2", "topic": "gn_home/gn-pi-zero-2/bme280/J"}
    {"time": "2023-01-03T12:10:10", "pm10": 0, "pm25": 0, "pm100": 1, "topic": "gn_home/gn-pi-zero-2/pm25/J"}
    """
    values = json.loads(line)   # values is a dict
    sens_dev = values['topic']  # TODO: should I strip off optional "/J" ending?
    if not sens_dev in sensor_devs:
        sensor_devs[sens_dev] = SensorVals(sens_dev)    # place to hold all future values for this device
        location,computer,sensor,_ = sens_dev.split('/')
        logger.debug('log_parse_json: {},{},{}'.format(location,computer,sensor))
    for fld_name in values:
        if fld_name == 'topic':
            continue
        val = values[fld_name]  # val is str
        if fld_name != 'time':
            val = float(val)
        sensor_devs[sens_dev].add_value(fld_name,val)

def show_sensor_devs():
    global sensor_devs
    logger.debug('sensor_dev keys')
    for key in sensor_devs:
        logger.debug('-- key = {}'.format(key))

def read_log(fname):
    '''
    Read sensor log files that are created by a separate MQTT client process.
    I generate a new file every day, so sensor data starts at midnight.
    :param fname: the log file name
    :return:
    '''
    with open(fname, 'r') as df:
        lines = df.readlines()
    for line in lines:
        log_parse_json(line)
    #show_sensor_devs()

def load_binary(filename):
    with open(filename, 'rb') as file_handle:
        return file_handle.read()
