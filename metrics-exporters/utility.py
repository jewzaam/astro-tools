import time
import re
import os

import prometheus_client

gauges = {}
counters = {}


def findNewestFile(directory, logfileregex):
    now=time.time()
    filemtimes = {}
    for root, _, files in os.walk(directory, topdown=False):
        for name in files:
            m = re.match(logfileregex, name)
            if m is not None:
                filename = os.path.join(root, name)
                mtime = os.path.getmtime(filename)
                if mtime >= now - 30*60:
                    # file was modified in the last 30 minutes.  consider it. else ignore it.
                    filemtimes[mtime] = filename
    s = sorted(filemtimes.items())
    if len(s) == 0:
        return None
    return s[-1][1]

def watchDirectory(logdir, logfileregex, frequencySeconds, callback):
    while True:
        newestLogFile = findNewestFile(logdir, logfileregex)
        while newestLogFile is None:
            time.sleep(frequencySeconds)
            newestLogFile = findNewestFile(logdir, logfileregex)

        currentLogFile = newestLogFile
        try:
            print("Loading log file: {}".format(currentLogFile))
            with open(currentLogFile, 'r') as f:
                while True:
                    where = f.tell()
                    line = f.readline()
                    if not line:
                        time.sleep(frequencySeconds)
                        newestLogFile = findNewestFile(logdir, logfileregex)
                        if newestLogFile is None or newestLogFile != currentLogFile:
                            # either the newest file is too old or there is a new file
                            # in either case, bail the inner loop so we get a fresh state from outer loop
                            break

                        f.seek(where)
                    else:
                        callback(line)
        except Exception as e:
            # print the error and try again with a delay (so it's not a hot fail lop)
            print(e)
            time.sleep(frequencySeconds)
            pass

def getGauge(name, description, labels):
    if name in gauges:
        gauge = gauges[name]
    else:
        print("Creating Gauge: {}({})".format(name,labels))
        gauge = prometheus_client.Gauge(name, description, labels)
        gauges[name] = gauge
    return gauge

def gteCounter(name, description, labels):
    if name in counters:
        counter = counters[name]
    else:
        print("Creating Counter: {}".format(name))
        counter = prometheus_client.Counter(name, description, labels)
        counters[name] = counter
    return counter

def set(name, value, labelDict):
    gauge = getGauge(name, "", labelDict.keys())
    if len(labelDict.keys()) > 0:
        gauge.labels(*labelDict.values()).set(value)
    else:
        gauge.set(value)

def add(name, value, labelDict):
    gauge = getGauge(name, "", labelDict.keys())
    if len(labelDict.keys()) > 0:
        gauge.labels(*labelDict.values()).inc(value)
    else:
        gauge.inc(value)

def inc(name, labelDict):
    counter = gteCounter(name, "", labelDict.keys())
    if len(labelDict.keys()) > 0:
        counter.labels(*labelDict.values()).inc()
    else:
        counter.inc()

def dec(name, labelDict):
    counter = gteCounter(name, "", labelDict.keys())
    if len(labelDict.keys()) > 0:
        counter.labels(*labelDict.values()).dec()
    else:
        counter.dec()

def metrics(port):
    prometheus_client.start_http_server(port)


