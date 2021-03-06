
import os
import sys
import redis
import ephem
import requests
from flask import Flask, render_template, redirect, jsonify
from json import loads, dumps
from NASA_PROBE_DSN import get_dsn_raw


app = Flask(__name__)

REDIS_URL = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
r_server = redis.StrictRedis.from_url(REDIS_URL)


@app.route('/')
def initial():
    return redirect("/dsn/probes.json", code=302)


@app.route('/dsn/mirror.json')

def dsn_mirror():
    """ a json view of the dsn xml feed """
    dsn = loads(r_server.get('dsn_raw_data'))
    return jsonify({'dsn': dsn}, 200)


@app.route('/dsn/probes.json')
@app.route('/dsn/spaceprobes.json')
def dsn_by_probe():
    """ dsn data aggregated by space probe """
    dsn_by_probe = loads(r_server.get('dsn_by_probe'))
    return jsonify({'dsn_by_probe': dsn_by_probe})

# for feeding the spaceprobes website


@app.route('/distances.json')
def all_probe_distances():
    """
        endpoint to feed the spaceprobes website
        this endpoint firsts asks the website what spaceprobes it has
        and returns something for each. 
       """
    # first get list of all probes from the webiste
    url = 'http://spaceprob.es/probes.json'
    all_probes_website = loads(requests.get(url).text)

    # get probes according to our DSN mirror
    dsn = loads(r_server.get('dsn_by_probe'))

    # now loop through probes on website and try to find their distances
    # some will have distances in dsn feed, others will have resource from website endpoint
    # and others we will use pyephem for their host planet
    distances = {}
    for probe in all_probes_website:

        dsn_name = probe['dsn_name']
        slug = probe['slug']

        if dsn_name and dsn_name in dsn:
            try:
                distances[slug] = dsn[dsn_name]['uplegRange']
            except KeyError:
                try:
                    distances[slug] = dsn[dsn_name]['downlegRange']
                except KeyError:
                    # there is no distance data
                    continue

        elif 'orbit_planet' in probe and probe['orbit_planet']:
            # this probe's distance is same as a planet, so use pyephem

            if probe['orbit_planet'] == 'Venus':
                m = ephem.Venus()
            if probe['orbit_planet'] == 'Mars':
                m = ephem.Mars()
            if probe['orbit_planet'] == 'Moon':
                m = ephem.Moon()
            if probe['orbit_planet'] == 'Earth-Moon-L2':
                m = ephem.Moon()

            if m:
                m.compute()
                earth_distance = m.earth_distance * 149597871  # convert from AU to kilometers

                if probe['orbit_planet'] == 'Earth-Moon-L2':
                    earth_distance = earth_distance + 72000  # approximation for E-M L2
                    # Queqiao orbits around Earth-Moon L2, which is distance of the
                    # Moon plus 65,000-80,000km

                distances[slug] = str(earth_distance)

        elif 'distance' in probe and probe['distance']:
            # this probe's distance is hard coded at website, add that
            try:
                # make sure this is actually numeric
                float(probe['distance'])
                distances[slug] = str(probe['distance'])
            except ValueError:
                pass

    return jsonify({'spaceprobe_distances': distances})


@app.route('/planets.json')
def planet_distances():
    """ return current distances from earth for 9 planets """
    meters_per_au = 149597870700

    planet_ephem = [ephem.Mercury(), ephem.Venus(), ephem.Mars(), ephem.Saturn(
    ), ephem.Jupiter(), ephem.Uranus(), ephem.Neptune(), ephem.Pluto()]
    planets = {}
    for p in planet_ephem:
        p.compute()
        planets[p.name] = p.earth_distance * meters_per_au / 10000  # km

    return jsonify({'distance_from_earth_km': planets})


# the rest of this is old and like wolfram alpha hacking or something..
def get_detail(probe):
    """ returns list of data we have for this probe
        url = /<probe_name>
    """
    try:
        wolframalpha = loads(r_server.get('wolframalpha'))
        detail = wolframalpha[probe]
        return detail
    except TypeError:  # type error?
        # this doesn't work i dunno
        return {'Error': 'spacecraft not found'}, 404


@app.route('/probes/guide/')
def guide():
    """ html api guide data viewer thingy
        at </probes/guide/>
    """
    try:
        wolframalpha = loads(r_server.get('wolframalpha'))
        kwargs = {'probe_details': wolframalpha}
        print(kwargs)
        return render_template('index.html', **kwargs)
    except:
        return redirect("/dsn/spaceprobes.json", code=302)


@app.route('/probes/<probe>/')
def detail(probe):
    """ returns list of data we have for this probe from wolfram alpha
        url = /<probe_name>
        ie
        </Cassini>
    """
    return get_detail(probe), 200


@app.route('/probes/<probe>/<field>/')
def single_field(probe, field):
    """ returns data for single field
        url = /<probe_name>/<field>
        ie
        </Cassini/mass>
    """
    field_value = get_detail(probe)
    print(field_value)
    return {field: field_value[field]}, 200


@app.route('/probes/')
def index():
    """ returns list of all space probes in db
        url = /
    """
    probe_names = [k for k in loads(r_server.get('wolframalpha'))]
    return {'spaceprobes': [p_ for p_ in probe_names]}, 200


# Happy coding!!!!!!!!!!!!!!!!!!!!!!!
if __name__ == '__main__':
    app.debug = True
    app.run()
