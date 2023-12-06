import network
import urequests
import ujson
import time
from datetime import datetime
import json
import machine # fuer realtimeclock rtc
from machine import Pin, PWM, Timer
import re

rtc = machine.RTC()

def getJson():
    r = urequests.get(url)
    jsonDate = r.headers['Date']
    jsonValues = r.json()
    r.close()
    return jsonValues, jsonDate
    
def setClockFromHumantime(humantime):
    # humantime = 'Wed, 22 Nov 2023 12:57:29 GMT'
    regex = "(\D\D\D),\s(\d\d)\s(\D\D\D)\s(\d\d\d\d)\s(\d\d):(\d\d):(\d\d)\s(\D\D\D)"
    e_search = re.search(regex,humantime)
    e_wday = e_search.group(1)
    e_mday = e_search.group(2)
    e_mon = e_search.group(3)
    e_year = e_search.group(4)
    e_hour = e_search.group(5)
    e_min = e_search.group(6)
    e_sec = e_search.group(7)
    e_tz = e_search.group(8)
    # print(e_wday, e_mday, e_mon, e_year, e_hour, e_min, e_sec, e_tz)
    # reformat time-tuple https://github.com/orgs/micropython/discussions/10616
    timeTuple = (int(e_year), {"Jan":1, "Feb":2, "Mar":3, "Apr":4, "May":5, "Jun":6, "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}[e_mon], int(e_mday), 0, int(e_hour), int(e_min), int(e_sec), 0)
    rtc.datetime(timeTuple)

def showValue():
    lastTimestamp = int(int(timestampNow/900)*900) # previous 15-minutes-value
    nextTimestamp = lastTimestamp + 900 # next 15-minutes-value
    lastValue = jsonValues[str(lastTimestamp)][1]
    nextValue = jsonValues[str(nextTimestamp)][1]
    thisValue = lastValue + (nextValue - lastValue)/900 * (timestampNow - lastTimestamp) # linear interpolation
    spannung = int(thisValue * 65535)
    if(spannung > 65535): spannung = 65535
    print(thisValue*100, '%')
    pwm.duty_u16(spannung)

def connectWiFi():
    wifiConnected = False # Mark flag so we can stop trying to connect
    wlan.disconnect()
    wlan.active(True)
    while (not wifiConnected): # while no1
        wlanTries = 3 # 20
        while (wlanTries > 0): # while no2
            print("Tries left: " + str(wlanTries))
            wlanTries -= 1
            print("Waiting for connection...")
            for networkName, networkPassword in wifiNetworks.items():
                ##Try next SSID
                if not wlan.isconnected():
                    print("Trying to connect to: " + networkName)
                    time.sleep(.1)
                    try:
                        wlan.connect(networkName, networkPassword)
                    except:
                        print("Failed to connect to: " + networkName)
                for i in range(3):
                    time.sleep(1)
                    if wlan.isconnected():
                        wifiConnected = True # Mark flag so we can stop trying to connect
                        break # break from while no2
                    waveMeter()
            if wlan.isconnected():
                break # break from while no1
        if wlanTries == 0:
            print('Too many tries to connect WiFi. Pause for 10 seconds and try again.')
            wlan.disconnect()
            wlan.active(False)
            setMeterZero()
            time.sleep(10)
    setMeterZero()
    print(wlan.ifconfig())



def disconnectWiFi():
    wlan.disconnect()
    wlan.active(False)
    print("Disconnecting WiFi and save energy")
    print()

# Fade the meter-needle from 0 to 100% and jump back to 0
def fadeMeter0to100():
    for i in range(202):
        # print(i)
        duty = i
        if (duty > 200):
            duty = 0
        if (duty > 100):
            duty = 100
        pwm.duty_u16(int(duty * 655.35))
        time.sleep(0.01)

# wave meter once from 15 to 75%
def waveMeter():
    for j in range(15,75):
        pwm.duty_u16(int(j * 655.35))
        time.sleep(0.01)
    for j in range(15,75):
        pwm.duty_u16(int((100-j) * 655.35))
        time.sleep(0.01)
    pwm.duty_u16(int(50 * 655.35))

def setMeterZero():
    pwm.duty_u16(0)

# initailize GPIO
pwm = PWM(Pin(1)) # Set GP1 as PWM-out (Pin 2 on RPi-board)
pwm.freq(1000) # Set the PWM frequency
pwm.duty_u16(0) # duty cycle = 0

# show that board has started succesfully
fadeMeter0to100()

# Define network
wlan = network.WLAN(network.STA_IF)

# load settings
filename = 'settings.json'
with open(filename, 'r') as f:
    settings = json.load(f)

url = settings['dataUrl']
wifiNetworks = settings['wifiNetworks']

while True:
    # Connect to network
    connectWiFi()
    # read json file and date from server
    jsonValues, jsonDate = getJson() 
    # print(jsonDate)
    # print(jsonValues)
    # disconnect and save energy
    disconnectWiFi()
    setClockFromHumantime(jsonDate)
    timestampNow = time.time()
    print('timestampNow: ', timestampNow)

    finalTimestamp = int(sorted(jsonValues.keys())[-3]) # get pre-pre-last object key (last one is 'timestamp')
    # finalTimestamp = timestampNow + 3 # zu Testzwecken nur 3 Sekunden zeigen
    if finalTimestamp > (timestampNow + 6*3600):
        finalTimestamp  = timestampNow + 6*3600 # maximum 6h from now

    while timestampNow < finalTimestamp:
        showValue()
        # print(time.gmtime(timestampNow))
        # print(rtc.datetime())
        # print(int(timestampNow), finalTimestamp)
        time.sleep(60)
        timestampNow = time.time() 
        
    print('Ende erreicht, lade aktuelleres JSON-File')
