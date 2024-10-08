Python application to display NEXRAD weather radar and forecasts for certain localities.
Forecasts are obtained from OpenWeather, but could be gotten from other sources.
This app runs in Flask. The NEXRAD display is strictly done by JavaScript code using the NWS (National Weather Service) API.
A separate project generates the NEXRAD code using nodeJS as a compiler; the HTML, JS and CSS files are placed in this app static directory.

The app is intended to run in WSGI. The deployment instructions that follow tell you how to setup on a Raspberry Pi.

Date: 2024-Feb-04

# Deployment

I based most of my installation on this tutorial: https://www.raspberrypi-spy.co.uk/2018/12/running-flask-under-nginx-raspberry-pi/

Install this project in /home/pi/wx or wherever makes sense to you.  
**sudo apt-get install nginx  
sudo apt-get install python3-pip  
sudo pip3 install flask uwsgi**  
Create a python virtualenv for this app using a recent Python 3.x. I put mine inside the app directory itself.
Activate the venv and install: **pip3 install matplotlib**.
The radar map displays are generated by JavaScript, so Python does not need basemap or cartopy.

Edit the file pi_uwsgi.ini which I have provided to reflect your directories.

Change owner of all files now:  
**sudo chown -R www-data /home/pi/wx**  

Assuming you've been following the tutorial that I referenced, you're now ready for _Step 7_.

I had trouble getting uwsgi to run my app properly, so I made frequent changes to **uwsgi.ini**.
Therefore the following alias is useful, since you may need to restart uwsgi.service a lot.   
**alias wsgirun='sudo systemctl daemon-reload; sudo systemctl restart uwsgi.service'**  





