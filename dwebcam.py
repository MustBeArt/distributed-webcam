#!/usr/bin/python

# distributed webcam processor CGI
# 2009-01-28 kb5mu
# 2024-02-15 kb5mu modified for Dreamhost hosting
#
# Remote webcam is expected to upload JPEG files with filenames like
#     fm-2009-01-28-21-40-PST.jpg
# or
#     fm-2009-01-28-21-40-PST~72.jpg
# to the upload_directory, and then hit this script with an argument
# of ?cam=fm
#
# The two-letter cam code ("fm" in the above example) can be used to
# distinguish multiple cams. Each one must have template, scratch, and
# upload directories with appropriate contents pre-installed, and must
# be mentioned in the caption data structure below.
#
# The optional value at the end is the temperature in degrees F.
# For negative temperatures, prefix an N, like this:
#     fm-2009-01-28-21-40-PST~N12.jpg
#

import cgi
#import cgitb; cgitb.enable()
import os
import sys
import re
import datetime
import shutil
import tempfile

# cgi.test()

upload_directory = "/home/paul_mba/mustbeart.com/webcam/upload"
webcam_directory = "/home/paul_mba/mustbeart.com/webcam"
scratch_directory = "/home/paul_mba/mustbeart.com/webcam/scratch"
template_directory = "/home/paul_mba/mustbeart.com/webcam/template"

keep_duration = datetime.timedelta(days=1)

night_threshold = 12000		# maximum bytes in a small "night" image

caption = {	'fm': 'Palomar Mountain',
			'xx': 'Unknown Webcam',
		  }

#============ End of Configuration ======================================

#
# This script doesn't make a user-visible web page, it just does some
# infrastructure processing. So, no need to make pretty HTML output.
# Easier to just output text for trace/debug purposes.
#
print "Content-Type: text/plain\n"

#
# We have a file uploaded, do everything required.
#
def process_uploaded_file(upfile_name, upfile_values):
	upfile_basename = upfile_name[0:-4]
	cam_dirname = webcam_directory + '/' + upfile_values['cam'] + '/'
	images_dirname = cam_dirname + 'images/'
	text = "%s %s-%s-%s %s:%s:00 %s" % (caption[upfile_values['cam']],
										upfile_values['year'],
										upfile_values['month'],
										upfile_values['day'],
										upfile_values['hour'],
										upfile_values['minute'],
										upfile_values['tz'])
	thumb_text = "%s:%s" % (upfile_values['hour'], upfile_values['minute'])
	scratch_dirname = tempfile.mkdtemp(prefix = upfile_values['cam']+'_', dir = scratch_directory)
	os.chdir(scratch_dirname)
	
	# Use ImageMagick in three steps to create a nice-sized, titled version.
	# The first step is to resize the original image and write a temp file.
	# This step ought to be combinable with the second step, but there seems
	# to be a bug in the -size parameter of the composite command that prevents
	# that from working correctly.
	print "  Building 640-pixel image ..."
	name_small = upfile_basename + "-small.jpg"
	status = os.system("/usr/bin/convert %s -resize 640x480 -unsharp 0 tmp640.png" % (upload_directory + '/' + upfile_name))
	if status:
		print "Failed to run convert"
		sys.exit()
	
	# Second step is to composite the temp file on top of a template that
	# contains a logo and room for text annotation outside the image area.
	status = os.system("composite -gravity North tmp640.png %s %s" % (template_directory + '/' + upfile_values['cam'] + '/' + '640titled.png', name_small))
	if status:
		print "Failed to run composite"
		sys.exit()

	# Third step is to add text to the composited image.
	status = os.system('mogrify -quality 50 -font DejaVu-Sans -pointsize 22 -fill white -undercolor black -gravity South -annotate 0 "%s" %s' % (text, name_small))
	if status:
		print "Failed to run mogrify"
		sys.exit()
	
	# Optional fourth step: add the temperature if it's available.
	temp = upfile_values['temp']
	if temp:
		if temp[0] == 'N':
			temp = str(-int(temp[1:]))		# N12 => -12
		temp = temp + '\xb0F'
		status = os.system('mogrify -quality 50 -font DejaVu-Sans -pointsize 24 -fill white -undercolor black -gravity SouthEast -annotate 0 "%s" %s' % (temp, name_small))
		if status:
			print "Failed to run mogrify"
			sys.exit()
		
	# Use ImageMagick, again in three steps, to create a thumbnail version.
	# The first step is to resize the original image and write a temp file.
	# This step ought to be combinable with the second step, but there seems
	# to be a bug in the -size parameter of the composite command that prevents
	# that from working correctly.
	print "  Building thumbnail ..."
	name_thumb = upfile_basename + "-thumb.jpg"
	status = os.system("/usr/bin/convert %s -resize 80x60 -unsharp 0 tmp80.png" % (upload_directory + '/' + upfile_name))
	if status:
		print "Failed to run convert"
		sys.exit()

	# Second step is to composite the temp file on top of a template that
	# contains a logo and room for text annotation outside the image area.
	status = os.system("composite -gravity North tmp80.png %s %s" % (template_directory + '/' + upfile_values['cam'] + '/' + '80titled.png', name_thumb))
	if status:
		print "Failed to run composite"
		sys.exit()

	# Third step is to add text to the composited image.
	status = os.system('mogrify -quality 50 -font DejaVu-Sans -pointsize 10 -fill white -undercolor black -gravity South -annotate 0 "%s" %s' % (thumb_text, name_thumb))
	if status:
		print "Failed to run mogrify"
		sys.exit()

	# Trim off all the metadata, making the thumbnail much smaller
	status = os.system('jhead -purejpg %s' % name_thumb)
	if status:
		print "Failed to run jhead"
		sys.exit()
		
	
	# use ImageMagick again to make a captioned version of the original image.
	# To put the caption outside the image area, we again have to composite the
	# image with a mostly-blank template of the right size, then add the caption.
	print "  Captioning camera image ..."
	status = os.system("composite -gravity North %s %s tmp1600.png" % (upload_directory + '/' + upfile_name, template_directory + '/' + upfile_values['cam'] + '/' + '1600titled.png'))
	if status:
		print "Failed to run composite"
		sys.exit()

	# Second step is to add text to the composited image.
	status = os.system('convert -quality 75 -font DejaVu-Sans -pointsize 24 -fill white -undercolor black -gravity South -annotate 0 "%s" tmp1600.png %s' % (text, upfile_name))
	if status:
		print "Failed to run convert"
		sys.exit()
	
	# Optional third step: add the temperature if it's available.
	if temp:
		status = os.system('mogrify -quality 50 -font DejaVu-Sans -pointsize 24 -fill white -undercolor black -gravity SouthEast -annotate 0 "%s" %s' % (temp, upfile_name))
		if status:
			print "Failed to run mogrify"
			sys.exit()
	

	# Move the created files into the webcam directory

	status = os.rename(upfile_name, images_dirname + upfile_name)
	os.rename(name_small,  images_dirname + name_small)
	os.rename(name_thumb,  images_dirname + name_thumb)

	# clean up the scratch directory
	os.remove('tmp1600.png')
	os.remove('tmp640.png')
	os.remove('tmp80.png')
	os.rmdir(scratch_dirname)
	
	print "  finished."


#=========================  MAIN PROGRAM  ==================================

#
# This script is called with an argument "cam" that is the two-letter code
# for which webcam this is. We will pay attention only to files that start
# with that code, so as to avoid accidentally processing partially-uploaded
# files from other webcams.
#
form = cgi.FieldStorage()
if form.has_key('cam'):
	thiscam = (form['cam'].value + '~~')[0:2];	# make sure it's two chars long	
	if caption.has_key(thiscam):
		print caption[thiscam]
	else:
		print "Unknown cam code %s provided!" % thiscam
		sys.exit()
else:
	print "No cam code provided!"
	sys.exit()

#
# The scheme requires that the uploaded files' names encode the date/time.
#       CC-YYYY-MM-DD-HHMM.jpg
# where:
#		CC is a two-letter code for which webcam this is
#		YYYY is the year when the picture was taken
#		MM is the month
#		DD is the day of the month
#		HH is the hour (local time)
#		MM is the minute
#
pattern = "^(?P<cam>%s)\-(?P<year>\d\d\d\d)\-(?P<month>\d\d)\-(?P<day>\d\d)\-(?P<hour>\d\d)(?P<minute>\d\d)\-(?P<tz>\w+)(~(?P<temp>\w+))?\.jpg$" % thiscam
filename_re = re.compile(pattern)

#
# Somehow the remote webcam(s) has/have arranged to upload its raw file(s)
# into the upload directory. Our task is to process all these files into
# whatever we need for the webcam web pages and remove them from the
# upload directory.
#

# get a list of everything in the upload directory right now
upfiles = os.listdir(upload_directory)

# process each file
for name in upfiles:
	path = upload_directory + "/" + name
	# There may be sub-directories and such; process only the actual files.
	# Upload failures often lead to empty files; skip those, too.
	if os.path.isfile(path) and os.path.getsize(path) > 0:
		# there may be files with improper names
		m = filename_re.match(name)
		if m:
			print "Processing " + name
			process_uploaded_file(name, m.groupdict())
			os.remove(path)
		else:
			print "Ignoring bogus file: " + name
			

# Now that we've processed the new file(s), go into the corresponding cam's
# images directory and update the web view. First we find the latest-dated
# image in the directory, and copy its large and small versions into files
# with standard fixed names, so that index.html can refer to them.
os.chdir(webcam_directory + '/' + thiscam + '/images')
camfiles = os.listdir('.')
if not camfiles:
	print "No images to summarize!"
	sys.exit()
latest = max(camfiles)			# this gets the original filename and not -small or -thumb
print "Latest image file is %s" % latest
shutil.copy(latest, "../latest.jpg")		# copy latest files
shutil.copy(latest[0:-4] + "-small.jpg", "../latest-small.jpg")

# extract date/time fields from the latest image
m = filename_re.match(latest)
latest_values = m.groupdict()
latest_dt = datetime.datetime(int(latest_values['year']), int(latest_values['month']), int(latest_values['day']), int(latest_values['hour']), int(latest_values['minute']))


#
# Pass through the files remaining in the images directory, removing all
# the files that are too old (according to keep_duration) and counting
# how many are left.
#
count = 0
for name in camfiles:
	m = filename_re.match(name)
	if m:
		values = m.groupdict()
		dt = datetime.datetime(int(values['year']), int(values['month']), int(values['day']), int(values['hour']), int(values['minute']))
		if latest_dt - dt >= keep_duration:
			print "Removing old image %s" % name
			os.remove(name)
			os.remove(name[0:-4] + "-small.jpg")
			os.remove(name[0:-4] + "-thumb.jpg")
		else:
			count = count + 1

print "Creating index and animation files for %d images." % count

#
# Pass through the reduced list of remaining files in the images directory,
# building new versions of webcam24.html and imageinit.js as we go.
#
camfiles = os.listdir('.')
camfiles.sort()					# process oldest to newest
i = 0

webcam24 = open('../webcam24.html', 'w')
imageinit = open('../imageinit.js', 'w')

# Copy the file header to webcam24.html
header = open(template_directory + '/' + thiscam + '/webcam24-header.html', 'r')
lines = header.readlines()
webcam24.writelines(lines)
header.close()

# Create the file header for imageinit.js
print >> imageinit, 'var imax=%d;' % count
print >> imageinit, 'image_files = new Array(imax);'
print >> imageinit, 'night = new Array(imax);'

# process each file.
for name in camfiles:
	m = filename_re.match(name)
	if m:
		values = m.groupdict()
		smallname = name[0:-4] + "-small.jpg"
		if os.path.getsize(smallname) > night_threshold:
			night = 0
		else:
			night = 1
		print >> webcam24, '<A HREF="images/%s-small.jpg"><IMG SRC="images/%s-thumb.jpg" HEIGHT=73 WIDTH=80 ALT="%s:%s" BORDER=0></A>&nbsp;' % (name[0:-4], name[0:-4], values['hour'], values['minute'])
		print >> imageinit, 'image_files[%d]="images/%s-small.jpg";' % (i, name[0:-4])
		print >> imageinit, 'night[%d]=%d;' % (i, night)
		i = i + 1

# Copy the file footer to webcam24.html
footer = open(template_directory + '/' + thiscam + '/webcam24-footer.html', 'r')
lines = footer.readlines()
webcam24.writelines(lines)
footer.close()
webcam24.close()

# Wrap up imageinit.js too
imageinit.close()

print "Finished!"


