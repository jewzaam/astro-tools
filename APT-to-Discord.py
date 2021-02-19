import requests
import os
import sys
from datetime import datetime
import yaml

## Image Processing libraries
from skimage import exposure, filters
import rawpy
import numpy
import imageio

jpg_filename=None

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

# returns:
#   * raw histogram peak percentage
#   * stretched histogram peak percentage
#   * is under exposed
#   * is over exposed
def raw_stretch_to_jpg(raw_filename, jpg_filename):

    out_raw_hist_p=-1.0
    out_str_hist_p=-1.0
    out_is_under_exp=True
    out_is_over_exp=True

    # Reference https://www.kaggle.com/tsilveira/raw-image-processing
    # Documentation https://scikit-image.org/docs/stable/index.html

    # I tried a few things out and found the following gets a good auto-stretch where stars and nebula are visible.
    # 1. adjust gamma, gamma=1, gain=1
    # 2. equalize histogram
    # 3. niblack threshold, window_size=9, k=1 (high window = blur, high k = darker with diminishing returns)
    # The goal is just to have a small reference image to send to Discord for checking drift over time without going outside..
    # It is NOT a goal to have a usable stretched image.  There is much better software and it requires human input.

    with rawpy.imread(raw_filename) as rawImg:
        rgbImg = rawImg.raw_image_visible
        gImg = exposure.adjust_gamma(rgbImg, gamma=1, gain=1)
        ghImg = exposure.equalize_hist(gImg)
        nibImg = filters.threshold_niblack(ghImg,window_size=9,k=1)
        # TODO look into streaming to requests instead of writing a file
        imageio.imwrite(jpg_filename, nibImg)

        # histogram calculations
        out_raw_hist_p,out_is_under_exp,out_is_over_exp=peak_histogram_percentage(rgbImg)
        out_str_hist_p,_,_=peak_histogram_percentage(nibImg)

        return out_raw_hist_p, out_str_hist_p, out_is_under_exp, out_is_over_exp

def log(message):
    with open("APT-to-Discord-py.log", 'a') as f:
        f.write("{}: {}\n".format(datetime.now(),message))


# Arguments: %LastFile% %CurrExp% %EDuration% %ETime% %PCBat% %CamBat% %CamSpace% %ExifT% <message>
try:
    log("command line arguments: \"{}\"".format("\", \"".join(sys.argv)))
    argLastFilename=sys.argv[1]
    argCurrExposure=sys.argv[2]
    argEstDuration=sys.argv[3]
    argEstCompletion=sys.argv[4]
    argPCBattery=sys.argv[5]
    argCamBattery=sys.argv[6]
    argCamSpace=sys.argv[7]
    argExifT=sys.argv[8]
    argMessage=sys.argv[9]

    # stretch raw and convert to jpg
    # also returns histogram info
    jpg_filename="{}.jpg".format(os.path.basename(argLastFilename).split(".")[0])
    raw_hist_peak_p,str_hist_peak_p,is_under_exp,is_over_exp=raw_stretch_to_jpg(argLastFilename, jpg_filename)

    # human readable "exposure" summary
    expA=[]
    if is_under_exp:
        expA.append("Under")
    if is_over_exp:
        expA.append("Over")

    expStr=" | ".join(expA) if len(expA)>0 else "Good"

    #Webhook of my channel. Click on edit channel --> Webhooks --> Creates webhook
    mUrl=""
    with open("config.yaml", "r") as c:
        mUrl=yaml.load(c, Loader=yaml.FullLoader)["webhook_url"]
    
    print(mUrl)

    # always send the text metadata
    short_filename=os.path.basename(argLastFilename)
    payload_json={
        "embeds": [
            {
                "title": argMessage,
                "description": "Filename: {}\nTime Remaining|ETA: {} | {}\nBattery PC|Camera: {}% | {}%\nHistogram RAW|Stretch: {:0.2f}% | {:0.2f}%\nExposure: {}".format(short_filename,argEstDuration,argEstCompletion,argPCBattery,argCamBattery,raw_hist_peak_p*100.0,str_hist_peak_p*100.0,expStr),
            },
        ],
    }
    log("request.json: {}".format(str(payload_json)))
    response = requests.post(mUrl, json=payload_json)
    log("response: {}".format(str(response.text)))

    # Try to send the stretched JPG.. does not yet handle large files so might fail.
    # Send the image separate from the metadata.  Fighting with getting the multipart form working, not worth the time.
    # https://birdie0.github.io/discord-webhooks-guide/structure/file.html
    # https://requests.readthedocs.io/en/master/user/quickstart/#post-a-multipart-encoded-file
    with open(jpg_filename, 'rb') as f:
        # json is ignored if files or data is used, pass in files
        log("request file: {}".format(jpg_filename))
        response = requests.post(mUrl, files={'file1': f})
        log(response.text)
except Exception as e:
    # unusual, print the stack by raising it
    log(str(e))
    raise e
finally:
    # cleanup the temporary file
    if jpg_filename is not None:
        os.remove(jpg_filename)