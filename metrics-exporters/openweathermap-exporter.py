import argparse
from types import LambdaType
import prometheus_client
import utility
import time
import requests
import json
import yaml
import re

METRICS_FREQUENCY_SECONDS=60

# cache for labels we may need to clear later, key is the metric from OWM (i.e. rain, snow, pop)
label_cache = {}

def getCurrentWeather(config):
    lat = config['location']['latidude']
    long = config['location']['longitude']
    api_key = config['openweathermap']['api_key']
    response = requests.get("http://api.openweathermap.org/data/2.5/onecall?appid={}&lat={}&lon={}&exclude=minutely,daily&units=metric".format(api_key,lat,long))

    if response.status_code != 200 or response.text is None or response.text == '':
        utility.inc("openweathermap_error_total")
    else:
        data = json.loads(response.text)

        global_labels={
            "latitude": data['lat'],
            "longitude": data['lon'],
        }

        utility.inc("openweathermap_success_total", global_labels)

        print(data)

        if 'current' in data:
            current = data['current']

            # note we have to clear any gauges we don't get data for.
            for key in label_cache: # check for any keys
                if key not in current and key not in ['pop','rain','snow']: # that are not in current root of data set except precipitation
                    for l in label_cache[key]:
                        utility.set("openweathermap_{}".format(key),None,l)
                        # https://stackoverflow.com/questions/11277432/how-can-i-remove-a-key-from-a-python-dictionary
                    # done processing, pop the cache so we don't keep doing this
                    _ = label_cache.pop(key, None)
            
            # process all the keys
            for key in current:
                value=current[key]
                if key=='temp':
                    l={"type": "current", "unit": "celsius"}
                    l.update(global_labels)
                    utility.set("openweathermap_temperature",value,l)
                if key=='feels_like':
                    l={"type": "feels_like", "unit": "celsius"}
                    l.update(global_labels)
                    utility.set("openweathermap_temperature",value,l)
                if key=='pressure':
                    l={"unit": "millibars"}
                    l.update(global_labels)
                    utility.set("openweathermap_{}".format(key),value,l)
                if key=='humidity':
                    l={"unit": "percent"}
                    l.update(global_labels)
                    utility.set("openweathermap_{}".format(key),value,l)
                if key=='dew_point':
                    l={"unit": "celsius"}
                    l.update(global_labels)
                    utility.set("openweathermap_{}".format(key),value,l)
                if key=='visibility':
                    l={"unit": "meters"}
                    l.update(global_labels)
                    utility.set("openweathermap_{}".format(key),value,l)
                if key=='clouds':
                    l={"unit": "percent"}
                    l.update(global_labels)
                    utility.set("openweathermap_{}".format(key),value,l)
                m = re.match('^wind_(.*)', key)
                if m:
                    t=m.groups()[0]
                    unit="kph"
                    if t=='deg':
                        t="direction"
                        unit="degree"
                    l={"type": t, "unit": unit}
                    l.update(global_labels)
                    utility.set("openweathermap_wind",value,l)

                if key=='dt':
                    l={"type": "current", "unit": "second"}
                    l.update(global_labels)
                    utility.set("openweathermap_time",int(value),l)

                if key=='sunrise':
                    now=time.time()
                    l={"type": "sunrise", "unit": "second"}
                    l.update(global_labels)
                    # api returns data per day.  if sunrise is too far in the past we can't do useful alerts.
                    # therefore if sunrise is more than 12 housr ago move it forward 1 day
                    # this is rough, but so is astronomical sunrise and sunset.. just needs to be good enough for alerts
                    sunrise=value
                    if sunrise<(now-12*60*60):
                        sunrise += 24*60*60
                    utility.set("openweathermap_time",int(sunrise),l)
                    l['type'] = 'astronomical_sunrise'
                    utility.set("openweathermap_time",int(sunrise)-20.0/360.0*float(60*60*24),l)
                if key=='sunset':
                    l={"type": "sunset", "unit": "second"}
                    l.update(global_labels)
                    # note unlike sunrise the sunset does not need to be adjusted.  API will flip to next day at midnight
                    utility.set("openweathermap_time",int(value),l)
                    l['type'] = 'astronomical_sunset'
                    utility.set("openweathermap_time",int(value)+20.0/360.0*float(60*60*24),l)

            # probability of precepitation (pop), rain, and snow are in the hourly forecast.  Just get the first entry.
            # TODO something more elegant than these individual booleans..
            found_hourly={
                'pop': False,
                'rain': False,
                'snow': False,
            }
            if 'hourly' in data and len(data['hourly']) > 0:
                for key in data['hourly'][0]:
                    if key=='pop':
                        found_hourly[key]=True
                        value=data['hourly'][0][key]
                        l={"unit": "percent"}
                        l.update(global_labels)
                        # inconsistency in data types, this is a percentage from 0.0 to 1.0
                        utility.set("openweathermap_{}".format(key),value*100,l)
                        if key not in label_cache:
                            label_cache[key]=[]
                        label_cache[key].append(l)
                    if key=='rain' or key=='snow':
                        found_hourly[key]=True
                        values=data['hourly'][0][key]
                        for x in values:
                            l={"type": x, "unit": "mm"}
                            l.update(global_labels)
                            utility.set("openweathermap_{}".format(key),values[x],l)
                            if key not in label_cache:
                                label_cache[key]=[]
                            label_cache[key].append(l)
            for key in found_hourly:
                if not found_hourly[key] and key in label_cache:
                    # we didn't find it in the data and we have it cached, so wipe metric
                    for l in label_cache[key]:
                        utility.set("openweathermap_{}".format(key),None,l)
                    _ = label_cache.pop(key, None)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Export logs as prometheus metrics.")
    parser.add_argument("--port", type=int, help="port to expose metrics on")
    parser.add_argument("--config", type=str, help="configuraiton file")
    
    args = parser.parse_args()
    
    # Start up the server to expose the metrics.
    prometheus_client.start_http_server(args.port)
    # Generate some requests.
    while True:
        config = {}
        with open(args.config, 'r') as f:
            config =  yaml.load(f, Loader=yaml.FullLoader)
        getCurrentWeather(config)
        time.sleep(config['openweathermap']['refresh_delay_seconds'])