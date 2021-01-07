# -*- coding: utf-8 -*-                 # NOQA

from jinja2 import Template,Environment,PackageLoader,select_autoescape,FileSystemLoader
import glob
import keys

def get_html():
    loader = FileSystemLoader('./templates')
    env = Environment(loader=loader)
    templ = env.get_template('radar.html')
    templ_args = {'google_maps_key' : keys.google_maps_key}
    rfiles = sorted(glob.glob('static/images/MUX*.gif'))
    images = [img.replace('\\','/') for img in rfiles]
    #images = ['1.gif', '2.gif', '3.gif']
    templ_args['imgs'] = images

    return templ.render(templ_args)

