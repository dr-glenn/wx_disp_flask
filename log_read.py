# Test program
# Read old-style log file, convert to JSON
import json
import logging
import my_logger
logger = my_logger.setup_logger(__name__,'log_read.log', level=logging.DEBUG)
sensor_devs = dict()
def log_parse_json(line):
    global sensor_devs
    """
    These are the log lines. It would be better if this was JSON
    gn_home/gn-pi-zero-2/pm25: time=2022-11-06T00:55:54,PM1_0=3,PM2_5=3,PM10_0=4
    {'gn_home/gn-pi-zero-2/pm25': {'time':'2022-11-06T00:55:54','PM1_0':3,'PM2_5':3,'PM10_0':4}}
    {'gn_home/gn-pi-zero-2/bme280': {'time':'2022-11-06T01:00:54','temp_c':16.8,'humidity':60.5,'pressure':1011.1}}
    """
    def _toJSON(line):
        ''' Convert the plain text line to JSON'''
        l = line.split(':',maxsplit=1)
        devkey = l[0]
        jout = '{{"{}" : {{'.format(devkey)
        vals = dict()
        ll = l[1].strip()
        ff = ll.split(',')
        for f in ff:
            fld_name, fld_val = f.split('=')
            vals[fld_name] = fld_val
            jout += '"{}":"{}",'.format(fld_name,fld_val)
        jout = jout[:-1] + '}}'
        #print('jout = '+jout)
        return jout
    x = _toJSON(line)
    values = json.loads(x)
    #print(type(values))
    sens_dev = list(values.keys())[0]
    if not sens_dev in sensor_devs:
        sensor_devs[sens_dev] = dict()
        location,computer,sensor = sens_dev.split('/')
        logger.debug('{},{},{}'.format(location,computer,sensor))
    #ll = line[fld1+1:].strip()
    for fld_name in values[sens_dev]:
        val = values[sens_dev][fld_name]
        if fld_name != 'time':
            val = float(val)
        sensor_devs[sens_dev][fld_name] = val

def read_log(fname):
    with open(fname, 'r') as df:
        lines = df.readlines()
    for line in lines:
        log_parse_json(line)
    for sens in sensor_devs:
        print('name={}, values={}'.format(sens,sensor_devs[sens]))


logfile='../sensors/mqtt_rcv.log'
read_log(logfile)