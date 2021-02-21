# rename-cr2.py

Rough script to take raw files and rename + move them to somewhere else based on EXIF data and some image processing (distinguish lights from darks).  The script is NOT fast as it's processing the raw image data.  It needs to know if a longer exposure is under exposed (a dark) or not (a light).

```script
rename-cr2.py <Source Base Directory> <Destination Base Directory>
```

Creates a structure like:

- Camera Name
  - YYYY-MM-DD
    - ISOXXXX
      - *Exposure*s
        - Dark
        - Light
      - Flat
      - Bias

# dss-info-to-csv.py

After processing images with DeepSkyStacker, extract metadata from DSS files and the image metadata to CSV.  Also does a histogram normalization and finds the highest percentage peak, useful to see where you'd be on a JPEG (stretched) histogram.

I have used this to review a bunch of shots at various shutter speeds and ISOs to find out the quality of the shots and if they're over or under exposed.

NOTE I need to enhance with logic now in the APT to Discord script that looks for both under and over exposing in the image.

# APT-to-Discord.py

Script to send image information from Astro Photography tool (APT) to a Discord webhook.
* Message
* Filename
* Time remaining in sequence
* Estimated time sequence will complete
* PC and camera battery %
* RAW and stretch histogram %
* Exposure info (if it's Good, Under exposed, or Over exposed)
* Stretched JPEG image

Must install requirements: `pip install -r requirements.txt`.  See Troubleshooting section.

And you must create a `config.yaml` with your discord webhook.

```yaml
webhook_url: https://discord.com/api/webhooks/someLongStringYouGotFromYourWebhook
```

## APT-to-Discord.vbs

APT didn't like running python directly.  But docs reference a vbscript.
So I wrote a simple wrapper around the python.


## **BEWARE!** of Quotes

APT script editor is crap.  It messes up quotation.  
For this to work you need to edit the script in the edit plan view.
Make sure only the vbs path and script are quoted. 
All command line arguments are NOT quoted, including any parameters.

Also I am taking specific arguments for stats sent to dropbox.  Extra args are raw text message.

Arguments expected will change over time as I get more gear.  For now it is:
* %LastFile%
* %CurrExp%
* %EDuration%
* %ETime%
* %PCBat%
* %CamBat%
* %CamSpace%
* %ExifT%
* any more arguments are appened with spaces and become extra message body.

DON'T QUOTE ARGUMENTS.  It does NOT work with quotes!

### Example Script

```shell
"<path>\APT-to-Discord.vbs" %LastFile% %CurrExp% %EDuration% %ETime% %PCBat% %CamBat% %CamSpace% %ExifT% Some Message
```

## Troubleshooting

"ImportError: DLL load failed while importing _remap: The specified module could not be found."

https://github.com/scikit-image/scikit-image/issues/4780

May need to:
1. (re)-install [Microsoft Visual C++ Redistributable for Visual Studio 2015, 2017 and 2019](https://support.microsoft.com/en-us/topic/the-latest-supported-visual-c-downloads-2647da03-1eea-4433-9aff-95f26a218cc0)
2. then, python -m pip install msvc-runtime

I have put all the suggested modulse in requirements.txt so you could also:

```shell
pip uninstall -m requirements.txt
pip install -m requirements.txt
```

# ATP_PlanExport.xml

Just dumping my APT plans so I can get back to older ones if I nuke something by accident.