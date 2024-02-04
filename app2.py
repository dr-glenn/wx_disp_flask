# testing to get uwsgi to run this with matplotlib

from flask import Flask, make_response, request, current_app, send_from_directory
import sys
import os
from functools import update_wrapper
from datetime import timedelta
app = Flask(__name__)
from pathlib import Path
Path('/home/pi/wx/app/touch0.txt').touch()
import logging
import my_logger
logger = my_logger.setup_logger(__name__,'ow.log', level=logging.DEBUG)
#import OpenWeatherProvider as ow
###### these are the imports in OpenWeatherProvider ############
import urllib
from urllib.request import urlopen,Request
from urllib.parse import urlencode
import json
import csv
import datetime as dt
import Config
import ApiKeys
from jinja2 import Environment, FileSystemLoader
import tail
#import timeplot
import tzinfo_4us as tzhelp
from Config import get_node_addr
###### these are the imports in timeplot ############
import io
import datetime as dt
import matplotlib
import matplotlib.pyplot as plt
import base64
import json
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
