import win32com.client
import time
import prometheus_client

import utility

# REFERENCE https://stackoverflow.com/questions/46163001/python-script-for-controlling-ascom-ccd-camera

REQUEST_TIME = prometheus_client.Summary('request_processing_seconds', 'Time spent processing request')

METRICS_PORT = 8000

METRICS_FREQUENCY_SECONDS = 2

drivers = {
    "switch": "ASCOM.pegasus_upb.Switch",
    "telescope": "ASCOM.DeviceHub.Telescope",
}

devices = {}

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
        # if we cannot connect then we cannot collect metrics.
        switch = getDevice('switch')
        switch.Connected = True
    except Exception as e:
        print(e)
        return

    success = False
    for i in range(switch.MaxSwitch):
        try:
            # Getting value may fail, if so we don't care about that switch.
            try:
                value = switch.GetSwitchValue(i)
            except:
                continue
            name = switch.GetSwitchName(i)
            labelDict = {"device_name": switch.Description, "index": i, "switch_name": name}
            utility.set("ascom_switch_data", value, labelDict)
            # if we set at least one metric we call it success
            success = True
        except Exception as e:
            print(e)
            pass
    
    if success:
        # keep count of how many times we collect these metrics
        utility.inc("ascom_switch_total", {"device_name": switch.Description})

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
    
    # collect all the data up front
    try:
        data = {
            'alignment_mode': scope.AlignmentMode,
            'altitude': scope.Altitude,
            'at_home': scope.AtHome,
            'at_park': scope.AtPark,
            'azimuth': scope.Azimuth,
            'declination': scope.Declination,
            'declination_rate': scope.DeclinationRate,
            'description': scope.Description,
            'guide_rate_declination': scope.GuideRateDeclination,
            'guide_rate_right_ascension': scope.GuideRateRightAscension,
            'is_pulse_guiding': scope.IsPulseGuiding,
            'name': scope.Name,
            'right_ascension': scope.RightAscension,
            'right_ascension_rate': scope.RightAscensionRate,
            'side_of_pier': scope.SideOfPier,
            'sidereal_time': scope.SiderealTime,
            'site_elevation': scope.SiteElevation,
            'site_latitude': scope.SiteLatitude,
            'site_longitude': scope.SiteLongitude,
            'slewing': scope.Slewing,
            'slew_settle_time': scope.SlewSettleTime,
            #'target_declination': scope.TargetDeclination,
            #'target_right_ascension': scope.TargetRightAscension,
            'tracking': scope.Tracking,
            'tracking_rate': scope.TrackingRate,
            'utc_date': scope.UTCDate,
        }
    except Exception as e:
        print(e)
        return

    utility.set("ascom_telescope_status", data['slewing'], {"name": data['name'], "data": "Slewing"})
    utility.set("ascom_telescope_status", data['at_home'], {"name": data['name'], "data": "AtHome"})
    utility.set("ascom_telescope_status", data['at_park'], {"name": data['name'], "data": "AtPark"})
    utility.set("ascom_telescope_status", data['alignment_mode'], {"name": data['name'], "data": "AlignmentMode"})
    utility.set("ascom_telescope_status", data['is_pulse_guiding'], {"name": data['name'], "data": "IsPulseGuiding"})
    utility.set("ascom_telescope_status", data['side_of_pier'], {"name": data['name'], "data": "SideOfPier"})
    utility.set("ascom_telescope_status", data['slew_settle_time'], {"name": data['name'], "data": "SlewSettleTime"})
    utility.set("ascom_telescope_status", data['tracking'], {"name": data['name'], "data": "Tracking"})

    utility.set("ascom_telescope_site_elevation", data['site_elevation'], {"name": data['name']})
    utility.set("ascom_telescope_site_latitude", data['site_latitude'], {"name": data['name']})
    utility.set("ascom_telescope_site_longitude", data['site_longitude'], {"name": data['name']})

    utility.set("ascom_telescope_altitude", data['altitude'], {"name": data['name']})
    utility.set("ascom_telescope_azimuth", data['azimuth'], {"name": data['name']})
    utility.set("ascom_telescope_declination", data['declination'], {"name": data['name']})
    utility.set("ascom_telescope_right_ascension", data['right_ascension'], {"name": data['name']})

    utility.set("ascom_telescope_rate", data['tracking_rate'], {"name": data['name'], "type": "Tracking"})
    utility.set("ascom_telescope_rate", data['declination_rate'], {"name": data['name'], "type": "Declination"})
    utility.set("ascom_telescope_rate", data['right_ascension_rate'], {"name": data['name'], "type": "RightAscension"})
    utility.set("ascom_telescope_rate", data['guide_rate_right_ascension'], {"name": data['name'], "type": "GuideRightAscension"})
    utility.set("ascom_telescope_rate", data['guide_rate_declination'], {"name": data['name'], "type": "GuideDeclination"})

    utility.inc("ascom_telescope_total", {"name": data['name']})

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