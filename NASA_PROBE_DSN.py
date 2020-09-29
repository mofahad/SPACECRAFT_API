import os
import sys
from datetime import datetime
from time import sleep, mktime
import requests
import redis
from json import loads, dumps
from urllib.request import urlopen
from xml.dom.minidom import parse
import xmltodict


REDIS_URL = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r_server = redis.StrictRedis.from_url(REDIS_URL)


def get_dsn_raw():
    timestamp = str(int(mktime(datetime.now().timetuple())))
    response = urlopen('https://eyes.nasa.gov/dsn/data/dsn.xml?r=' + timestamp)
    dom_parse = parse(response)

    dsn_data = {}
    for node in dom_parse.childNodes[0].childNodes:

        if not hasattr(node, 'tagName'):
            continue

        if node.tagName == 'station':

            xmltodict.parse(node.toprettyxml())

            station = node.getAttribute('friendlyName')
            # print(station)
            dsn_data.setdefault(station, {})
            # print(dsn_data)
            dsn_data[station]['friendlyName'] = node.getAttribute(
                'friendlyName')
            dsn_data[station]['timeUTC'] = node.getAttribute('timeUTC')
            dsn_data[station]['timeZoneOffset'] = node.getAttribute(
                'timeZoneOffset')
            # print(dsn_data)

        if node.tagName == 'dish':

            dsn_data[station].setdefault('dishes', []).append(
                xmltodict.parse(node.toxml())['dish'])

    r_server.set('dsn_raw_data', dumps(dsn_data))
    # print(dsn_data)
    return dsn_data


# Now  from here we  going to convert dsn_data


def convert_dsn_data():

    dsn_data = loads(r_server.get('dsn_raw_data'))
   # print(dsn_data)
   # print("#"*30)

    dsn_probe_data = {}
    #dsn_raw =dsn_data
    dsn_lst = []
    # dsn_data
   # dsn_probe_data = {}

    for station in dsn_data:

        for dish_attr in dsn_data[station]:

            timeUTC = dsn_data[station]['timeUTC']
            timeZoneOffset = dsn_data[station]['timeZoneOffset']
           # timeZoneOffset =dsn_data[station]['timezoneOffset']
            # print(timeUTC)
            # print(timeZoneOffset)
            try:

                dish_list = dsn_data[station]['dishes']
            except KeyError:

                continue
            # print(type(dish_list))

            for dish in dish_list:
                try:

                    downSignal = dish['downSignal']
                except KeyError:
                    pass
                try:
                    upSignal = dish['upSignal']
                except KeyError:
                    pass
                if not upSignal and not downSignal:
                    # if no down or upsignal move along
                    continue
                dish_name, target = dish['@name'], dish['target']

               # last_updated , created_on  =  dish['']

                last_created, updated = dish['@created'], dish['@updated']

                azimuthAngle, elevationAngle = dish['@azimuthAngle'], dish['@elevationAngle']
                # print(type(downSignal))
                # print(type(upSignal))
                # print(type(target))
                if type(downSignal).__name__ == 'dict':
                    # print("eeeeeee") for debugging
                    downSignal = [downSignal]
                if type(upSignal).__name__ == 'dict':

                    upSignal = [upSignal]
                if type(target).__name__ == 'dict':
                   # print("$$$$$$$$$$$$$")
                    target = [target]
               # print(type(target))

                for _ in target:
                   # print(type(_))

                    probe = _['@name']
                    # print(type(_))
                    dsn_probe_data.setdefault(probe, {})
                    # Don't want @ that's why doing K[1:], removing @
                    probe_data = {k[1:]: v for k, v in _.items()}
                    # print(probe_data)

                    if float(_['@uplegRange']) > 0:

                       # only update if there is a distance measurement
                        dsn_probe_data[probe]['downlegRange'] = _[
                            '@downlegRange']
                        dsn_probe_data[probe]['uplegRange'] = _['@uplegRange']
                        dsn_probe_data[probe]['rtlt'] = _['@rtlt']
                        dsn_probe_data[probe]['last_contact'] = last_created
                        dsn_probe_data[probe]['last_dish'] = dish_name
                        dsn_probe_data[probe]['updated'] = updated
                        dsn_probe_data[probe]['station'] = station
                        dsn_probe_data[probe]['azimuthAngle'] = azimuthAngle
                        dsn_probe_data[probe]['elevationAngle'] = elevationAngle

                        dsn_lst.append(probe)

                    else:

                        print('uplegRange < 0 for ' +
                              probe + ' ' + _['@uplegRange'])

    if dsn_lst:
        print('*'*125)

        r_server.set('dsn_by_probe', dumps(dsn_probe_data))
        # print(dsn_probe_data)
        # r_server.set('dsn_by_probe', dumps(dsn_by_probe))

        print("*"*125)
        print("updated: " + ", ".join(sorted(list(set(dsn_probe_data)))))

    else:
        print("no updates!!!!!!!")


# def get_current_probes():

    #url = 'https://murmuring-anchorage-8062.herokuapp.com/dsn/mirror.json'

    # for p, v in loads(requests.get(url).text).items():

       # return sorted([n for n in v])


if __name__ == '__main__':
    get_dsn_raw()

    convert_dsn_data()

    #s = get_current_probes()

    # print(s)
