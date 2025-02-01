# testing to get uwsgi to run this with matplotlib

from flask import Flask
import sys

app = Flask(__name__)
from pathlib import Path
Path('/home/pi/wx/app/touch0.txt').touch()
import logging
import my_logger
logger = my_logger.setup_logger(__name__, '../ow.log', level=logging.DEBUG)
#import OpenWeatherProvider as ow
###### these are the imports in OpenWeatherProvider ############
#import timeplot
###### these are the imports in timeplot ############
###### these are the imports in timeplot ############

# There are two import problems:
# 1. matplotlib
# 2. Possibly it is bad to import logging and my_logger more than once. NO problem.

Path('/home/pi/wx/app/touch1.txt').touch()

@app.route("/")
def index():
    logger.info('Hey, somebody asked for me.')
    output = "<html><body><h1>Test site running under Flask</h1><p>{}</p></body></html>".format(sys.path)
    #output = "<html><body><h1>Test site running under Flask</h1><p>{}</p></body></html>".format(os.environ['PYTHONPATH'])
    return output

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
