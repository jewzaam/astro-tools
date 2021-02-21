import os
from pathlib import Path
import sys
import math
import yaml

# to read tag data
import exifread

# to get histogram
from skimage import exposure, filters
import rawpy
import numpy

if len(sys.argv)<=2:
    print("usage: {} <input base directory> <output base directory> {}".format(sys.argv[0],"|".join(sys.argv)))
    sys.exit(-2)

input_base_directory=sys.argv[1]
output_base_directory=sys.argv[2]

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
            sys.stdout.write("\rProcessing images: {:01.2f}%".format(math.floor(float(psn)/float(count)*10000.0)/100.0))
            p=os.path.join(dirpath, filename)
            file_data={
                "filename": p
            }

            # load histogram and find maximum peak and collect the % of total histogram graph where that shows up
            raw_hist_p,is_under_exp,is_over_exp,stretch_hist_p=None,None,None,None
            with rawpy.imread(p) as rawImg:
                rgbImg=rawImg.raw_image_visible
                gImg = exposure.adjust_gamma(rgbImg, gamma=1, gain=1)
                ghImg = exposure.equalize_hist(gImg)
                nibImg = filters.threshold_niblack(ghImg,window_size=9,k=1)

                # histogram calculations
                raw_hist_p,is_under_exp,is_over_exp=peak_histogram_percentage(rgbImg)
                stretch_hist_p,_,_=peak_histogram_percentage(nibImg)

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
            image_type=""
            new_directory="{}\\{}\\{}\\ISO{}".format(output_base_directory,camera_name,image_datetime.split('T')[0].replace(':','-'),iso_speed)
            if exp_time>=1:
                # lights and darks are in seconds, not subseconds, but nuances of timing can make it appear so
                exp_time=math.floor(exp_time)
                if is_under_exp:
                    image_type="Dark"
                else:
                    image_type="Light"
                # bias and flats don't have exposure time in directory but darks and lights do
                new_directory="{}\\{}s".format(new_directory,exp_time)
                # add in the exposure time to filename
                new_filename="{}_ISO{}_{}_{}s.{}".format(image_type[0],iso_speed,image_datetime,exp_time,extension)
            else:
                if exp_time<1.0/1000.0:
                    image_type="Bias"
                else:
                    image_type="Flat"
                new_filename="{}_ISO{}_{}.{}".format(image_type[0],iso_speed,image_datetime,extension)
            
            # add the type to the directory
            new_directory+="\\"+image_type

            # create the new directory
            Path(new_directory).mkdir(parents=True,exist_ok=True)

            # move the file
            os.replace(file_data['filename'], "{}\\{}".format(new_directory,new_filename))
