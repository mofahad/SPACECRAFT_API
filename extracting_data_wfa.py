import os
import json
import redis
import wolframalpha

REDIS_URL = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
APP_ID = os.getenv('WOLFRAMALPHA_APP_ID', 'RJLYTE-U3R6TAQ4TP')

print('APP_ID :::##' + APP_ID)

r_server = redis.StrictRedis.from_url(REDIS_URL)
client = wolframalpha.Client(APP_ID)

# get list of space probes
file_name = 'C:/Users/Dell/Desktop/NASA_DSN_PROBE_DATA/active_probes.txt'
probe_names = []
with open(file_name) as f:
    content = f.readlines()
    for l in content[1:]:  # first line is a comment
        probe_names.append(l.strip())

# lookup in wolframalpha each probe
probe_data = {}
for probe in probe_names:

    probe_data[probe] = {}
    lookup_str = probe + ' spacecraft'
    print("#"*123)
    print('looking up: ' + lookup_str)
    print("#"*123)

    res = client.query(lookup_str)
    print(type(res))
    for pod in res.pods:  # the first one is funky version of spacecraft name
        if not pod.text:
            print('no wolphramalph text found for ' + lookup_str)
            continue

        data_chunk = pod.text

        for line in data_chunk.split("\n"):
            attr = line.split('|')[0].strip()
            value = [l.strip() for l in line.split('|')[1:]]
            if len(value) == 1:
                value = value[0]
            if value:
                probe_data[probe][attr] = value
    print(probe_data)

r_server.set('wolframalpha', json.dumps(probe_data))
