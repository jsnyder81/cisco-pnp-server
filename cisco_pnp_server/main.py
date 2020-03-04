import re
from flask import Flask, request, send_from_directory, render_template, Response
from pathlib import Path

import requests
import xmltodict
import pprint as pp
import json

app = Flask(__name__, template_folder="templates")
current_dir = Path(__file__)

### CHANGE THIS TO MATCH YOUR IP
host = "192.168.10.187"
port = 8443


with open('inventory_jake.json') as f:
    DEVICES = json.load(f)

SERIAL_NUM_RE = re.compile(r'PID:(?P<product_id>\S+),VID:(?P<hw_version>\S+),SN:(?P<serial_number>\S+)')
SERIAL_NUM_RE2 = re.compile(r'PID:(?P<product_id>\S+),SN:(?P<serial_number>\S+)')


def work_request(host, type="device_info"):
    url = f"http://{host}/pnp/WORK-REQUEST"
    with open(current_dir / f"{type}.xml") as f:
        data = f.read()
    return requests.post(url, data)


def get_device_info(host):
    url = f"http://{host}/pnp/WORK-REQUEST"
    # response =


@app.route('/test-xml')
def test_xml():
    result = render_template('load_config.xml', correlator_id="123", config_filename="test.cfg", udi="123")
    return Response(result, mimetype='text/xml')


@app.route('/')
def root():
    return 'Hello Stream!'


@app.route('/configs/<path:path>')
def serve_configs(path):
    return send_from_directory('configs', path)


@app.route('/images/<path:path>')
def serve_sw_images(path):
    return send_from_directory('sw_images', path)


@app.route('/pnp/HELLO')
def pnp_hello():
    print("Hello")
    return '', 200


@app.route('/pnp/WORK-REQUEST', methods=['POST'])
def pnp_work_request():
    print(request.data)
    data = xmltodict.parse(request.data)
    #pp.pprint(data)
    #print(data['pnp']['info']['deviceId']['hostname'])
    hostname = data['pnp']['info']['deviceId']['hostname']
    #print(type(hostname))
    udi = data['pnp']['@udi']
    correlator_id = data['pnp']['info']['@correlator']
    udi_match = SERIAL_NUM_RE.match(udi)
    if udi_match is None or udi_match.group('serial_number' != 0):
        print("Null")
        sudi = data['pnp']['info']['deviceId']['SUDI']
        udi_match = SERIAL_NUM_RE2.match(sudi)
    serial_number = udi_match.group('serial_number')
    #print(DEVICES[serial_number]["hostnameSet"])
    if (hostname.startswith("AP"), DEVICES[serial_number]["hostnameSet"]) == (True, False):
        result_data = ap_rename(udi, correlator_id, serial_number)
        DEVICES[serial_number]["hostnameSet"] = True
    else:
        result_data = load_config(udi, correlator_id, serial_number)
        print(result_data)
    return Response(result_data, mimetype='text/xml')


def load_config(udi, correlator_id, serial_number):
    config_filename = DEVICES[serial_number]["config-filename"]
    jinja_context = {
        "udi": udi,
        "correlator_id": correlator_id,
        "config_filename": config_filename,
        "host": host,
        "port": port
    }
    result_data = render_template('load_config.xml', **jinja_context)
    return result_data


def ap_rename(udi, correlator_id, serial_number):
    jinja_context = {
        "udi": udi,
        "correlator_id": correlator_id,
        "deviceName": DEVICES[serial_number]["deviceName"]
    }
    result_data = render_template('set_ap_name.xml', **jinja_context)
    #pp.pprint(result_data)
    return result_data


@app.route('/pnp/WORK-RESPONSE', methods=['POST'])
def pnp_work_response():
    print(request.data)
    data = xmltodict.parse(request.data)
    correlator_id = data['pnp']['response']['@correlator']
    udi = data['pnp']['@udi']
    jinja_context = {
        "udi": udi,
        "correlator_id": correlator_id,
    }
    result_data = render_template('bye.xml', **jinja_context)
    #pp.pprint(result_data)
    return Response(result_data, mimetype='text/xml')


if __name__ == '__main__':
    app.run(port=port , debug=True, host=host)