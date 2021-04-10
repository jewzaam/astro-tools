import requests
import sys
from datetime import datetime
import yaml
import os

# NINA runs scripts in it's directory and we can't write to it.  Nor are config files located there.
rootPath=os.path.dirname(os.path.realpath(__file__))

def log(message):
    with open("{}/NINA-to-Discord-py.log".format(rootPath), 'a') as f:
        f.write("{}: {}\n".format(datetime.now(),message))

# Arguments: %LastFile% %CurrExp% %EDuration% %ETime% %PCBat% %CamBat% %CamSpace% %ExifT% <message>
try:
    if sys.argv and len(sys.argv) > 1:
        title=sys.argv[1]
    
    message="\n".join(sys.argv[2:])

    #Webhook of my channel. Click on edit channel --> Webhooks --> Creates webhook
    mUrl=""
    with open("{}/config.yaml".format(rootPath), "r") as c:
        mUrl=yaml.load(c, Loader=yaml.FullLoader)["webhook_url"]
    
    # always send the text metadata
    payload_json={
        "embeds": [
            {
                "title": title,
                "description": "{}".format(message),
            },
        ],
    }
    print(payload_json)
    response = requests.post(mUrl, json=payload_json)
    print(response.text)
except Exception as e:
    # unusual, print the stack by raising it
    log(str(e))
    raise e