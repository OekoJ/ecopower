import requests
import time
import json
from datetime import datetime

timestampNow = int(int(time.time()/900)*900) # rounded to last 15 minutes value, timestamp in seconds
timestamp24hAgo = timestampNow - (24*60*60) # seconds

# https://smard.api.proxy.bund.dev/app/chart_data/411/DE/index_quarterhour.json
# 411 - Prognostizierte Erzeugung: Gesamt | 411 statt 122
def getLastUpdateTimestamp(filter):
    url = 'https://smard.api.proxy.bund.dev/app/chart_data/' + str(filter) + '/DE/index_quarterhour.json'
    # print('https://smard.api.proxy.bund.dev/app/chart_data/' + str(filter) + '/DE/index_quarterhour.json')
    r = requests.get(url)
    allTimestamps = r.json()
    # print(json.dumps(allTimestamps, indent=2))
    return allTimestamps['timestamps'] # all timestamps
    
def getValuesPerCategory(filter,timestamp):
    url = 'https://smard.api.proxy.bund.dev/app/chart_data/' + str(filter) + '/DE/' + str(filter) + '_DE_quarterhour_' + str(timestamp) + '.json'
    # print('https://smard.api.proxy.bund.dev/app/chart_data/' + str(filter) + '/DE/' + str(filter) + '_DE_quarterhour_' + str(timestamp) + '.json')
    r = requests.get(url)
    try:
       decodedResult = r.json()
    except:
       return []
    return decodedResult['series']

# https://smard.api.bund.dev/

# collect pre-last and last values in one array
updateTimestamp = getLastUpdateTimestamp(411)[-2] # fetch pre-last timestamp, timestamp in milliseconds
prognostizierteErzeugungOnshore = getValuesPerCategory(123,updateTimestamp) # 123 - Prognostizierte Erzeugung: Onshore
prognostizierteErzeugungOffshore = getValuesPerCategory(3791,updateTimestamp) # 3791 - Prognostizierte Erzeugung: Offshore
prognostizierteErzeugungPhotovoltaik = getValuesPerCategory(125,updateTimestamp) # 125 - Prognostizierte Erzeugung: Photovoltaik
prognostizierteErzeugungGesamt = getValuesPerCategory(411,updateTimestamp) # 411 - Prognostizierte Erzeugung: Gesamt
stromerzeugungWasserkraft = getValuesPerCategory(1226,updateTimestamp) # 1226 - Stromerzeugung: Wasserkraft
stromerzeugungBiomasse = getValuesPerCategory(4066,updateTimestamp) # 4066 - Stromerzeugung: Biomasse

updateTimestamp = getLastUpdateTimestamp(411)[-1] # fetch last timestamp, timestamp in milliseconds 
prognostizierteErzeugungOnshore += getValuesPerCategory(123,updateTimestamp) # 123 - Prognostizierte Erzeugung: Onshore
prognostizierteErzeugungOffshore += getValuesPerCategory(3791,updateTimestamp) # 3791 - Prognostizierte Erzeugung: Offshore
prognostizierteErzeugungPhotovoltaik = getValuesPerCategory(125,updateTimestamp) # 125 - Prognostizierte Erzeugung: Photovoltaik
prognostizierteErzeugungGesamt += getValuesPerCategory(411,updateTimestamp) # 411 - Prognostizierte Erzeugung: Gesamt
stromerzeugungWasserkraft += getValuesPerCategory(1226,updateTimestamp) # 1226 - Stromerzeugung: Wasserkraft
stromerzeugungBiomasse += getValuesPerCategory(4066,updateTimestamp) # 4066 - Stromerzeugung: Biomasse

werteTabelle = {'timestamp': ['humantime','percent','wind_onshore','wind_offshore','solar','water','biomass','total']}

# print("Timestamp:", timestampNow)
# print(datetime.fromtimestamp(timestampNow).strftime('%Y-%m-%d %H:%M'))

def fillWerteTabelle(zeitreiheLonglist, position, offset):
    for zeitwert in zeitreiheLonglist:
        if int(zeitwert[0]/1000) + offset >= int(timestampNow):
            thisTimestamp = int(zeitwert[0]/1000) + offset
            wert = zeitwert[1]
            if werteTabelle.get(thisTimestamp) is None:
                werteTabelle[thisTimestamp] = [datetime.fromtimestamp(thisTimestamp).strftime('%Y-%m-%d %H:%M'), 0, 0, 0, 0, 0, 0, 0] 
            werteTabelle[thisTimestamp][position] = wert
            if (int(zeitwert[0]/1000) >= int(timestampNow) + (24*60*60)):
                break # no more than 24h in future

fillWerteTabelle(prognostizierteErzeugungOnshore, 2, 0)
fillWerteTabelle(prognostizierteErzeugungOffshore, 3, 0)
fillWerteTabelle(prognostizierteErzeugungPhotovoltaik, 4, 0)
fillWerteTabelle(stromerzeugungWasserkraft, 5, 24*60*60) # 24h ago for water
fillWerteTabelle(stromerzeugungBiomasse, 6, 24*60*60) # 24h ago for biomass
fillWerteTabelle(prognostizierteErzeugungGesamt, 7, 0)

# calculate percentages
for thisTimestamp in list(werteTabelle): # prevent RuntimeError: dictionary changed size during iteration
    if str(thisTimestamp).isdigit():
        try:
            # calculate: [1] = ([2]+[3]+[4]+[5]+[6])/[7]
            werteTabelle[thisTimestamp][1] = round((werteTabelle[thisTimestamp][2] + werteTabelle[thisTimestamp][3] + werteTabelle[thisTimestamp][4] + werteTabelle[thisTimestamp][5] + werteTabelle[thisTimestamp][6])/werteTabelle[thisTimestamp][7], 4)
        except:
            del werteTabelle[thisTimestamp] # remove directory entries without valid percentage value 

# print('Aktueller Wert um ' + werteTabelle[timestampNow][0] + ': ' + str(round(werteTabelle[timestampNow][1]*100, 1)) + '%')

# write json file - Change this path to the location you want to pick the json from
filename = "/var/www/vhosts/example.com/httpdocs/oekostrom/ecopower.json"
with open(filename, 'w') as fp:
    json.dump(werteTabelle, fp, indent=4)