# dss info to csv

After processing images with DeepSkyStacker, extract metadata from DSS files and the image metadata to CSV.  Also does a histogram normalization and finds the highest percentage peak, useful to see where you'd be on a JPEG (stretched) histogram.

I have used this to review a bunch of shots at various shutter speeds and ISOs to find out the quality of the shots and if they're over or under exposed.

NOTE I need to enhance with logic now in the APT to Discord script that looks for both under and over exposing in the image.

# APT to Discord

Astro Photography tool (APT) didn't like running python directly.  But docs reference a vbscript.
So I wrote a simple wrapper around the python.

Also must install requirements: `pip install -r requirements.txt`

And you must create a `config.yaml` with your discord webhook.

```yaml
webhook_url: https://discord.com/api/webhooks/someLongStringYouGotFromYourWebhook
```

## **BEWARE!**

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