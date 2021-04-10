import win32com.client
import time
import prometheus_client

# REFERENCE https://stackoverflow.com/questions/46163001/python-script-for-controlling-ascom-ccd-camera

REQUEST_TIME = prometheus_client.Summary('request_processing_seconds', 'Time spent processing request')

METRICS_PORT = 8000

METRICS_FREQUENCY_SECONDS = 2

gauges = {}

counters = {}

drivers = {
    "switch": "ASCOM.pegasus_upb.Switch",
    "camera": "ASCOM.DSLR.Camera",
    "telescope": "ASCOM.DeviceHub.Telescope",
}

devices = {}

def metricName(names):
    return "_".join(names).lower().replace(" ", "_")

def getGauge(names, description):
    metric_name = metricName(names)
    if metric_name in gauges:
        gauge = gauges[metric_name]
    else:
        print("Creating Gauge: {}".format(metric_name))
        gauge = prometheus_client.Gauge(metric_name, description)
        gauges[metric_name] = gauge
    return gauge

def getCounter(names, description):
    metric_name = metricName(names)
    if metric_name in counters:
        counter = counters[metric_name]
    else:
        print("Creating Counter: {}".format(metric_name))
        counter = prometheus_client.Counter(metric_name, description)
        counters[metric_name] = counter
    return counter

def chooseDriver(deviceType):
    x = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    x.DeviceType = deviceType
    driver = x.Choose(None)
    print("Device type '{}', driver is: {}".format(deviceType, driver))
    return driver

def getDevice(deviceType):
    if deviceType in drivers:
        driver = drivers[deviceType]
    else:
        driver = chooseDriver(deviceType)

    if driver in devices:
        device = devices[driver]
    else:
        device = win32com.client.Dispatch(driver)
        devices[driver] = device

        # connect to the device
        device.Connected = True
        print("Connected to '{}'".format(device.Description))
    return device

def getMetrics_Switch():
    # https://ascom-standards.org/Help/Developer/html/T_ASCOM_DriverAccess_Switch.htm

    try:
        # if we cannot connect then we cannot collect metrics.  no biggie, don't fail the app
        switch = getDevice('switch')
        switch.Connected = True
    except Exception as e:
        print(e)
        return

    for i in range(switch.MaxSwitch):
        try:
            # Getting value may fail, if so we don't care about that switch.
            try:
                value = switch.GetSwitchValue(i)
            except:
                continue
            name = switch.GetSwitchName(i)
            gauge = getGauge([switch.Description, name], switch.GetSwitchDescription(i))
            gauge.set(value)
            getCounter([switch.Description, name, "count"], "Count of times data collected for Switch '{} / {}'".format(switch.Description, switch.GetSwitchDescription(i))).inc()
        except Exception as e:
            print(e)
            pass
    
    # keep count of how many times we collect these metrics
    getCounter([switch.Description, "count"], "Count of times data collected for Switch '{}'".format(switch.Description)).inc()

def getMetrics_Telescope():
    # https://ascom-standards.org/Help/Developer/html/T_ASCOM_DriverAccess_Telescope.htm

    try:
        # print error if cannot connect but don't cause things to fail
        scope = getDevice('telescope')
        scope.Connected = True
    except Exception as e:
        print(e)
        return

    if not scope.Connected:
        return

    data = {
        'alignment_mode': scope.AlignmentMode,
        'altitude': scope.Altitude(),
        'at_home': scope.AtHome(),
        'at_park': scope.AtPark(),
        'azimuth': scope.Azimuth(),
        'declination': scope.Declination(),
        'declination_rate': scope.DeclinationRate(),
        'description': scope.Description(),
        'guide_rate_declination': scope.GuideRateDeclination(),
        'guide_rate_right_ascention': scope.GuideRateRightAscention(),
        'is_pulse_guiding': scope.IsPulseGuiding(),
        'name': scope.Name(),
        'right_ascention': scope.RightAscention(),
        'right_ascention_rate': scope.RightAscentionRate(),
        'side_of_pier': scope.SideOfPier(),
        'sidereal_time': scope.SiderealTime(),
        'site_elevation': scope.SiteElevation(),
        'site_latitude': scope.SiteLatitude(),
        'site_longitude': scope.SiteLongitude(),
        'slewing': scope.Slewing(),
        'slew_settle_time': scope.SlewSettleTime(),
        'target_declination': scope.TargetDeclination(),
        'target_right_ascention': scope.TargetRightAscention(),
        'tracking': scope.Tracking(),
        'tracking_rate': scope.TrackingRate(),
        'utc_date': scope.UTCDate(),
    }

    return data

@REQUEST_TIME.time()
def getMetrics():
    getMetrics_Switch()
    getMetrics_Telescope()

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    prometheus_client.start_http_server(METRICS_PORT)
    # Generate some requests.
    while True:
        getMetrics()
        time.sleep(METRICS_FREQUENCY_SECONDS)