import os
from pathlib import Path
import sys
import math
import datetime

# to read tag data
import exifread

# linear image processing
import rawpy
import numpy

if len(sys.argv)<=3:
    print("usage: {} <input base directory> <output base directory> <Target Name>".format(sys.argv[0]))
    sys.exit(-2)

input_base_directory=sys.argv[1]
output_base_directory=sys.argv[2]
target_name=sys.argv[3]

raw_ext=["cr2", "tif", "tiff", "fit", "fits", "raw"]

def peak_histogram_percentage(img,bins=5000):
    hist,_=numpy.histogram(img,bins=bins)

    # macro analysis, want bins = 100
    hist_exp=None
    if bins==100:
        hist_exp=hist
    else:
        hist_exp,_=numpy.histogram(img,bins=100)
    
    # find peak
    peak_bin=-1
    peak_value=-1
    total_values=0
    for i in range(0,len(hist)-1):
        total_values+=hist[i]
        if (hist[i-1]<hist[i] or hist[i]>hist[i+1]) and hist[i]>peak_value:
            peak_bin=i
            peak_value=hist[i]

    # check if we are clipping by seeing if there's a high amount of data in lowest and highest bins
    # setting by % of total data.  if we see > 1% call it clipping
    under_exp_threshold=0.001
    over_exp_threshold=0.01
    is_under_exp=True if hist_exp[0] / total_values > under_exp_threshold else False
    is_over_exp=True if hist_exp[-1] / total_values > over_exp_threshold else False

    return float(peak_bin)/float(len(hist)), is_under_exp, is_over_exp

# find all raw image files and count them
count=0
for dirpath, dirnames, filenames in os.walk(input_base_directory):
    for filename in filenames:
        if filename.lower().split('.')[-1] in raw_ext and not filename.lower().startswith("master"):
            count+=1

# process each file
psn=0
for dirpath, dirnames, filenames in os.walk(input_base_directory):
    for filename in filenames:
        if filename.lower().split('.')[-1] in raw_ext and not filename.lower().startswith("master"):
            psn+=1
            sys.stdout.write("\rProcessing images: {:01.2f}% ({} of {})".format(math.floor(float(psn-1)/float(count)*10000.0)/100.0,psn,count))
            p=os.path.join(dirpath, filename)
            file_data={
                "filename": p
            }

            # load image metadata
            with open(p, 'rb') as f:
                tags=exifread.process_file(f, details=False)
                for tag in tags.keys():
                    if tag != 'JPEGThumbnail' and tags[tag] is not None:
                        file_data[tag]=str(tags[tag])

            # construct filename
            # LIGHTS: if exposure >= 1 second and there is data (peak is > bin 1/100) 
            # DARKS: if exposure >= 1 second and it is not LIGHTS
            # BIAS: if exposure < 1/1000 second
            # FLATS: if exposure 

            camera_name=file_data['Image Model']
            image_datetime=file_data['EXIF DateTimeOriginal'].replace(' ','T').replace(':','-')
            iso_speed=file_data['EXIF ISOSpeedRatings']
            exp_time=math.ceil(eval(file_data['EXIF ExposureTime'])*10000.0)/10000.0
            #focal_length=file_data['EXIF FocalLength']
            extension=filename.split(".")[-1]

            # for date we want the "night" not actual calendar date, so images are grouped together.
            # therefore, take the timestamp and subtract 12 hours
            half_day=datetime.timedelta(hours=12)
            d=datetime.datetime.strptime(image_datetime, '%Y-%m-%dT%H-%M-%S')
            image_date=str(d-half_day).split(' ')[0]

            image_type=""
            new_directory=""
            if exp_time>=1:
                # identify if it's under exposed so we know if it was a dark
                # load histogram and find maximum peak and collect the % of total histogram graph where that shows up
                with rawpy.imread(p) as rawImg:
                    # histogram calculations
                    _,is_under_exp,_=peak_histogram_percentage(rawImg.raw_image_visible)

                    if is_under_exp:
                        image_type="Dark"
                    else:
                        image_type="Light"
                # lights and darks are in seconds, not subseconds, but nuances of timing can make it appear so
                exp_time=math.floor(exp_time)
                # bias and flats don't have exposure time in directory but darks and lights do
                new_directory="{}\\{}\\{}\\{}\\ISO{}\\{}s\\{}".format(output_base_directory,camera_name,target_name,image_date,iso_speed,exp_time,image_type)
                # add in the exposure time to filename
                new_filename="{}_{}_ISO{}_{}_{}s.{}".format(image_type[0],target_name,iso_speed,image_datetime,exp_time,extension)
            else:
                if exp_time<1.0/1000.0:
                    image_type="Bias"
                    # bias isn't specific to the shoot.  if I got them we care about the camera, iso, and date (not time) only
                    new_directory="{}\\{}\\{}+ISO{}+{}".format(output_base_directory,camera_name,image_type,iso_speed,image_date)
                else:
                    image_type="Flat"
                    # flats matter for camera, date, and iso
                    new_directory="{}\\{}\\{}\\{}\\{}+ISO{}".format(output_base_directory,camera_name,image_date,image_type,iso_speed)
                new_filename="{}_ISO{}_{}.{}".format(image_type[0],iso_speed,image_datetime,extension)
            
            # create the new directory
            Path(new_directory).mkdir(parents=True,exist_ok=True)

            # move the file
            os.replace(file_data['filename'], "{}\\{}".format(new_directory,new_filename))
