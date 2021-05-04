# ASCOM Exporter
Export metrics from ASCOM.  Currently supports:
* 1 x telescope (aka mount)
* 1 x switch
* 2 x cameras

Configuration isn't well managed, it's in code at this time.  Edit the `drivers` dictionary.

To discover device names run with the `--choose` option.

Depending on the device you use it may fail.  Only the camera logic is robust enough to survive individual properties not being implemented.  So... may not work for you but it's a starting point if you want to hack on it for your purposes.  Happy to take suggestions and PR's!

```shell
python ascom-exporter.py --port 8000
```

# Log Exporter

Export logs as metrics by parsing them.  Configs are in yaml files.  Takes arguments for:
* port
* config file
* log directory
* log file regex

Provided are exporter configurations for NINA and PHD2.

## NINA Logs
```shell
python log-exporter.py --port 8001 --config log-exporter-nina.yaml --logdir "%AppData%\Local\NINA\Logs" --logfileregex ".*\.log"
```

## PHD2 Logs
```shell
python log-exporterv --port 8002 --config log-exporter-phd2.yaml --logdir "%Documents%\PHD2" --logfileregex "PHD2_GuideLog.*[0-9]\.txt"
```

# Open Weather Map Exporter

Exports weather based on openweathermap.org data using free API's.  Requires a config file with the api key.

```shell
python openweathermap-exporter.py --port 8003 --config openweathermap-exporter.yaml
```

Example config with fake API key
```yaml
location:
  latidude: 34.8754
  longitude: -81.4567
degrees_to_astronomical_sunrise: 20
degrees_to_astronomical_sunset: 20
openweathermap:
  api_key: myapikeyis12346567890
  refresh_delay_seconds: 60
```

* location = the latitude / longitude you want to monitor
* degrees_to_astronomical_sunrise = imperfect math (and buggy) but 20* seems pretty close
* degrees_to_astronomical_sunset = imperfect math (and buggy) but 20* seems pretty close
* openweathermap.api_key = your api key
* openweathermap.refresh_delay_seconds = time between pulling new metrics
