import argparse
from types import LambdaType
import prometheus_client
import utility
import time
import requests
import json
import yaml

OWM_APIKEY="d25e30bc8f75ed10708fae36ffae6df2"

METRICS_FREQUENCY_SECONDS=60

# cache for labels we may need to clear later, key is the metric from OWM (i.e. rain, snow, pop)
label_cache = {}

def getCurrentWeather(config):
    lat = config['location']['latidude']
    long = config['location']['longitude']
    api_key = config['openweathermap']['api_key']
    response = requests.get("http://api.openweathermap.org/data/2.5/weather?appid={}&lat={}&lon={}".format(api_key,lat,long))
    # TODO convert http://api.openweathermap.org/data/2.5/onecall?appid={}&lat={}&lon={}&exclude=minutely,daily&units=metric

    if response.status_code != 200 or response.text is None or response.text == '':
        utility.inc("openweathermap_error_total")
    else:
        data = json.loads(response.text)

        global_labels={
            "latitude": data['coord']['lat'],
            "longitude": data['coord']['lon'],
        }

        utility.inc("openweathermap_success_total", global_labels)

        # note we have to clear any gauges we don't get data for.
        for key in label_cache: # check for any keys
            if key not in data: # that are not in current root of data set
                for l in label_cache[key]:
                    utility.set("openweathermap_{}".format(key),None,l)
                    # https://stackoverflow.com/questions/11277432/how-can-i-remove-a-key-from-a-python-dictionary
                # done processing, pop the cache so we don't keep doing this
                _ = label_cache.pop(key, None)

        for key in data:
            temp=None
            humidity=None

            if key=='main':
                if 'temp' in data[key]:
                    l={"type": "current", "unit": "kelvin"}
                    l.update(global_labels)
                    temp=data[key]['temp']
                    utility.set("openweathermap_temperature",temp,l)
                if 'feels_like' in data[key]:
                    l={"type": "feels_like", "unit": "kelvin"}
                    l.update(global_labels)
                    utility.set("openweathermap_temperature",data[key]['feels_like'],l)
                if 'temp_min' in data[key]:
                    l={"type": "min", "unit": "kelvin"}
                    l.update(global_labels)
                    utility.set("openweathermap_temperature",data[key]['temp_min'],l)
                if 'temp_max' in data[key]:
                    l={"type": "max", "unit": "kelvin"}
                    l.update(global_labels)
                    utility.set("openweathermap_temperature",data[key]['temp_max'],l)
                if 'pressure' in data[key]:
                    l={"unit": "millibars"}
                    l.update(global_labels)
                    utility.set("openweathermap_pressure",data[key]['pressure'],l)
                if 'humidity' in data[key]:
                    l={"unit": "percent"}
                    l.update(global_labels)
                    humidity=data[key]['humidity']
                    utility.set("openweathermap_humidity",humidity,l)

            # if we have temp and humidity calculate dew point
            # what sucks is humidity is based on C or F (not sure how much it matters) but NOT K!
            # so why do they have it as % and not dew point?!?  so stupid...
            if temp is not None and humidity is not None:
                # convert temp to C
                temp_c=temp-273.15
                # calculate dew point in C
                dew_point_k=temp_c*(humidity/100.0)+273.15
                l={"unit": "kelvin"}
                l.update(global_labels)
                utility.set("openweathermap_dew_point",dew_point_k,l)

            if key=='visibility':
                l={"unit": "meters"}
                l.update(global_labels)
                utility.set("openweathermap_{}".format(key),data[key],l)

            if key=='wind':
                for x in data[key]:
                    l={"type": x, "unit": "mph"}
                    l.update(global_labels)
                    if x == 'deg':
                        l['unit'] = "degree"
                        l['type'] = "direction"
                    utility.set("openweathermap_{}".format(key),data[key][x],l)

            if key=='clouds':
                for x in data[key]:
                    l={"type": x, "unit": "percent"}
                    l.update(global_labels)
                    utility.set("openweathermap_{}".format(key),data[key][x],l)

            if key=='pop':
                # pop = probability of precipitation
                l={"unit": "percent"}
                l.update(global_labels)
                utility.set("openweathermap_{}".format(key),data[key*100],l)
                label_cache[key]=[l] # we need an array for the label cache, pop has a single entry

            if key=='rain':
                label_cache[key]=[]
                for x in data[key]:
                    l={"type": x, "unit": "mm"}
                    l.update(global_labels)
                    utility.set("openweathermap_{}".format(key),data[key][x],l)
                    label_cache[key].append(l)
            
            if key=='snow':
                label_cache[key]=[]
                for x in data[key]:
                    l={"type": x, "unit": "mm"}
                    l.update(global_labels)
                    utility.set("openweathermap_{}".format(key),data[key][x],l)
                    label_cache[key].append(l)

            if key=='dt':
                l={"type": "current", "unit": "second"}
                l.update(global_labels)
                utility.set("openweathermap_time",int(data[key]),l)

            if key=='sys':
                now=time.time()
                if 'sunrise' in data[key]:
                    l={"type": "sunrise", "unit": "second"}
                    l.update(global_labels)
                    # api returns data per day.  if sunrise is too far in the past we can't do useful alerts.
                    # therefore if sunrise is more than 12 housr ago move it forward 1 day
                    # this is rough, but so is astronomical sunrise and sunset.. just needs to be good enough for alerts
                    sunrise=data[key]['sunrise']
                    if sunrise<(now-12*60*60):
                        sunrise += 24*60*60
                    utility.set("openweathermap_time",int(sunrise),l)
                    l['type'] = 'astronomical_sunrise'
                    utility.set("openweathermap_time",int(sunrise)-20.0/360.0*float(60*60*24),l)
                if 'sunset' in data[key]:
                    l={"type": "sunset", "unit": "second"}
                    l.update(global_labels)
                    # note unlike sunrise the sunset does not need to be adjusted.  API will flip to next day at midnight
                    utility.set("openweathermap_time",int(data[key]['sunset']),l)
                    l['type'] = 'astronomical_sunset'
                    utility.set("openweathermap_time",int(data[key]['sunset'])+20.0/360.0*float(60*60*24),l)


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