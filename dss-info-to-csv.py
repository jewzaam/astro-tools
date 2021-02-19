import os
import sys
import math

# to read tag data
import exifread

# to get histogram
from skimage import exposure, filters
import rawpy
import numpy

output="dss-info-to-csv.csv"
headers=[]

if len(sys.argv)>1:
    output=sys.argv[1]

data=[]

# find all raw image files and count them
count=0
for dirpath, dirnames, filenames in os.walk(os.getcwd()):
    for filename in [out for out in filenames if out.endswith(".CR2")]:
        count+=1

# process each file
psn=0
for dirpath, dirnames, filenames in os.walk(os.getcwd()):
    for filename in [out for out in filenames if out.endswith(".CR2")]:
        psn+=1
        sys.stdout.write("\rProcessing images: {:01.2f}%".format(math.floor(float(psn)/float(count)*10000.0)/100.0))
        p=os.path.join(dirpath, filename)
        file_data={
            "filename": p
        }

        # load histogram and find maximum peak and collect the % of total histogram graph where that shows up
        with rawpy.imread(p) as rawImg:
            rgbImg=rawImg.raw_image_visible
            gImg = exposure.adjust_gamma(rgbImg, gamma=1, gain=1)
            ghImg = exposure.equalize_hist(gImg)
            nibImg = filters.threshold_niblack(ghImg,window_size=9,k=1)

            # use the stretched image, get histogram
            hist,_=numpy.histogram(nibImg,bins=200)
            peak_bin=-1
            peak_value=-1
            for i in range(0,len(hist)-1):
                if (hist[i-1]<hist[i] or hist[i]>hist[i+1]) and hist[i]>peak_value:
                    peak_bin=i
                    peak_value=hist[i]
            file_data['Histogram Peak Percentage']=str(float(peak_bin)/float(len(hist)))

        # load image metadata
        with open(p, 'rb') as f:
            tags=exifread.process_file(f, details=False)
            for tag in tags.keys():
                if tag != 'JPEGThumbnail' and tags[tag] is not None:
                    file_data[tag]=str(tags[tag])

        # load DSS info
        with open("{}.Info.txt".format(p.split('.')[0]), 'r') as f:
            for line in f:
                line=line.strip()
                # if we find a line starting in "Star#" we're pass general info, we can skip the rest of the file
                if line.startswith("Star#"):
                    break
                try:
                    a=line.split("=")
                    key=a[0].strip()
                    value=a[1].strip()
                    file_data[key]=str(value)
                except:
                    # couldn't process it, next!
                    break
        
        # update headers
        headers=list(set(headers) | set(file_data.keys()))

        # add data
        data.append(file_data)


with open(output, 'w') as out:
    # write headers
    sorted_headers=sorted(headers)
    out.write("\"")
    out.write("\",\"".join(sorted_headers))
    out.write("\"\n")

    # write data
    for row in data:
        values=[]
        for key in sorted_headers:
            if key not in row:
                values.append("")
                continue
            values.append(row[key])
        out.write("\"")
        out.write("\",\"".join(values))
        out.write("\"\n")