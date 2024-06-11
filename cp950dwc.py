#!/usr/bin/python

#
# Nikon CP-950 feeding the distributed webcam system
# 2009-01-28 kb5mu
# lots of edits lost to history
# 2014-11-27 kb5mu adapted to run on Raspberry Pi (Raspbian)
#
# Use an external scheduler to run this script periodically,
# in a directory where nobody else is creating files.
#
# This script relies on server-side processing to present the webcam results
# to users. All it does is grab a photo, give it a filename that encodes the
# date (and maybe the temperature), and upload it to a given directory on the
# distributed webcam host. It then hits a CGI script on the host to trigger
# an update of the web pages.
#
# If the network is unavailable, the photo files accumulate and are uploaded
# on a future attempt when the network is available again.
#

import os
from os import environ
import time
import urllib.request, urllib.parse, urllib.error
import glob
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

camcode = "fm"		# Fern Meadow
# camcode = "xx"			# test configuration
CGI_URL = "https://www.mustbeart.com/cgi-bin/dwebcam.py?cam=%s" % camcode

camera_port = "/dev/ttyUSB0"

host = "mustbeart.com"
# port = 64050                     # default for SSH is 22
user = "paul_mba"
upload_dir = "/home/paul_mba/mustbeart.com/webcam/upload/"
archive_dirname = "archive/"

APRS_path = "/var/wxreport.txt"

wx_name = "Fern Meadow"

#============ End of Configuration ====================================

def pause_and_exit():
#	print "Exit in 10 seconds ..."
#	time.sleep(10)				# 10 seconds
	sys.exit()
        

def get_APRS_temp():
        if not os.path.exists(APRS_path):
                return None
        
        with open(APRS_path) as f:
                datestamp = f.readline()
                aprsdata  = f.readline()
        
        temptm = time.strptime(datestamp, "%b %d %Y %H:%M\n")
        temptm1 = (temptm.tm_year, temptm.tm_mon, temptm.tm_mday, temptm.tm_hour, temptm.tm_min, temptm.tm_sec, temptm.tm_wday, temptm.tm_yday, 0)
        tempdate = time.mktime(temptm1)
        #tempdate = time.mktime(time.strptime(datestamp, "%b %d %Y %H:%M\n"))
        currentdate = time.mktime(time.gmtime())
        if abs(currentdate-tempdate) > 300:
                print("Temperature data is stale: ", datestamp)
                return None
                
        return int(aprsdata[12:15])
	
def get_ambient_weather_temp():
    wx_url = f"{environ['AMBIENT_ENDPOINT']}/devices?applicationKey={environ['AMBIENT_APPLICATION_KEY']}&apiKey={environ['AMBIENT_API_KEY']}"

    r = requests.get(wx_url)
    if r.status_code != 200:
        print(f"Received status code {r.status_code}")
        return None
    else:
        devices = r.json()
        for device in devices:
            wx_age = time.mktime(time.gmtime()) - 3600 - \
                     time.mktime(time.strptime(device['lastData']['date'], '%Y-%m-%dT%H:%M:%S.000Z'))
            wx_station_name = device['info']['name']
            if wx_age <= 300 and wx_station_name == wx_name: 
                return device['lastData']['tempf']
        return None

if time.localtime().tm_isdst:
        tz = "PDT"
else:
        tz = "PST"

t = get_APRS_temp() or get_ambient_weather_temp()
if not t:
        temp = ""
elif t < 0:
        temp = "~N%d" % -t
else:
        temp = "~%d" % t

filename = time.strftime(camcode + "-%%Y-%%m-%%d-%%H%%M-%s%s.jpg" % (tz,temp))
print(filename)

cmd = "photopc -l %s clock eraseall flash Off snapshot image 1 %s" % (camera_port, filename)
#try up to three times to command the camera; this seems to help.
status = os.system(cmd) and os.system(cmd) and os.system(cmd)
if status:
	print("Failed to command the camera")
	# Try to upload files anyway, just in case we can.

files = glob.glob('*.jpg')
if not files:
	print("No JPEG files to upload!")
	pause_and_exit()

print("Attempting to upload %d files ..." % len(files))
for f in files:
	print(f, "... ", end=' ')
	sys.stdout.flush()
	# cmd = "scp -P %d %s %s@%s:%s%s" % (port, f,user,host,upload_dir,f)
	cmd = "scp %s %s@%s:%s%s" % (f,user,host,upload_dir,f)
	print(cmd, "... ", end=' ')
	os.system(cmd) and os.system(cmd) and os.system(cmd)
	os.rename(f, archive_dirname + f)
	print("done.")

print("Notifying distributed webcam server ...")
#print("=================================================================")
print("Server response: " + urllib.request.urlopen(CGI_URL).read().decode("utf-8").rstrip())
#print("=================================================================")
pause_and_exit()
