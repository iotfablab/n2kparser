#!/usr/bin/env python3

from subprocess import Popen, PIPE
import sys
import os
import json
import concurrent.futures
import time
import signal
import logging
import argparse

from influxdb import InfluxDBClient, line_protocol
import paho.mqtt.publish as publish

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

handler = logging.FileHandler("/var/log/n2kparser.log")
handler.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s-%(name)s-%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

DEVICE = ''
client = None
n2k_conf = dict()
mqtt_conf = dict()
analyzer_process = None

def save_to_db(measurments):
    """ Save NMEA2000 values to InfluxDB"""
    global client
    try:
        client.send_packet(measurments)
        return True
    except Exception as e:
        logger.error('Error while UDP sending: {}'.format(e))
        return False


def publish_data(pgn_value, lineprotocol_data):
    lp_array = lineprotocol_data.split('\n')
    lp_array.pop() # remove last newline
    publish_msgs = []
    global n2k_conf
    global mqtt_conf
    for topic in n2k_conf['pgnConfigs'][str(pgn_value)]['topics']:
        mqtt_msg = {
            'topic': DEVICE + '/' + topic,
            'payload': lp_array[n2k_conf['pgnConfigs'][str(pgn_value)]['topics'].index(topic)],
            'qos': 1,
            'retain': False
        }
        publish_msgs.append(mqtt_msg)
    logger.debug(publish_msgs)
    try:
        publish.multiple(
            publish_msgs,
            hostname=mqtt_conf['broker'],
            port=mqtt_conf['port']
        )
        return True
    except Exception as e:
        logger.error('Publish Error: {}'.format(e))
        return False
        



def read_nmea2k():
    """Read the actisense-serial -r {device} | analyzer -json for given NMEA2000 NGT-1 device port"""
    # Actisense-Serial
    actisense_process = Popen(['actisense-serial', '-r', n2k_conf['port']], stdout=PIPE)

    # Analyzer Stream for output in JSON
    global analyzer_process
    analyzer_process = Popen(['analyzer', '-json'], stdin=actisense_process.stdout, stdout=PIPE, stderr=PIPE)
    PGNs = list(map(int, n2k_conf['pgnConfigs'].keys()))
    logger.debug('PGNs: {}'.format(PGNs))

    while True:
        incoming_json = analyzer_process.stdout.readline().decode('utf-8')
        try:
            incoming_data = json.loads(incoming_json)

            if incoming_data['pgn'] in PGNs:
                # remove unnecessary keys
                del incoming_data['dst']
                del incoming_data['prio']
                
                # check if the configuration for the PGN has the `fromSource` Key
                if 'fromSource' in list(n2k_conf['pgnConfigs'][str(incoming_data['pgn'])].keys()):
                    logger.info('PGN Source Filter Check')
                    if incoming_data['src'] != n2k_conf['pgnConfigs'][str(incoming_data['pgn'])]['fromSource']:
                        logger.info('PGN: {} with src: {}'.format(incoming_data['pgn'], incoming_data['src']))
                        logger.info('Skipping data for: {}'.format(incoming_data['description']))
                        continue
                
                measurement = {
                    "tags": {
                        "source": "nmea2k",
                        "PGN": incoming_data['pgn'],
                        "src": incoming_data['src']
                    },
                    "points": []
                }

                # Create a set of all available fields from the incoming frame
                incoming_fields = set(incoming_data['fields'].keys())
                fields_from_conf = set(n2k_conf['pgnConfigs'][str(incoming_data['pgn'])]['fieldLabels'])
                logger.debug('Fields To Log: {f}'.format(f=fields_from_conf.intersection(incoming_fields)))
                
                # Get all the Fields necessary to be stored into InfluxDB
                for selected_field in fields_from_conf.intersection(incoming_fields):
                    # Measurement name is the profile type name e.g. control/environment/engine etc available
                    # as the first level for the mqtt topics
                    meas_name = n2k_conf['pgnConfigs'][str(incoming_data['pgn'])]['topics'][0].split('/')[0]
                    point = {
                        "measurement": meas_name,
                        "time": int(time.time() * 1e9),
                        "fields": {}
                    }
                    point['fields'][selected_field.replace(" ", "")] = incoming_data['fields'][selected_field]
                    measurement['points'].append(point)
                # logger.debug(line_protocol.make_lines(measurement))

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    if executor.submit(save_to_db, measurement).result():
                        logger.info('saved to InfluxDB')
                    if executor.submit(publish_data, incoming_data['pgn'], line_protocol.make_lines(measurement)).result():
                        logger.info('Published data successfully')
                time.sleep(0.05)

        except Exception as e:
            logger.exception(e)


def file_path(path_to_file):
    """Check if Path and File exist for Configuration"""

    if os.path.exists(path_to_file):
        if os.path.isfile(path_to_file):
            logger.info('File Exists')
            with open(path_to_file) as conf_file:
                return json.load(conf_file)
        else:
            logger.error('Configuration File Not Found')
            raise FileNotFoundError(path_to_file)
    else:
        logger.error('Path to Configuration File Not Found')
        raise NotADirectoryError(path_to_file)


def parse_args():
    """Parse Arguments for configuration file"""

    parser = argparse.ArgumentParser(description='CLI to store Actisense-NGT Gateway values to InfluxDB and publish via MQTT')
    parser.add_argument('--config', type=str, required=True, help='Provide the configuration conf.json file with path')
    return parser.parse_args()

def main():
    """Step ups for Clients and Configuration """
    args = parse_args()

    CONF = file_path(args.config)
    global DEVICE
    DEVICE = CONF['deviceID']
    global n2k_conf
    n2k_conf = CONF['n2k']
    influx_conf = CONF['influx']

    global mqtt_conf
    mqtt_conf = CONF['mqtt']
    
    logger.info('Creating InfluxDB client')
    logger.debug('Client for {h}@{p} with udp:{ud}'.format(h=influx_conf['host'], p=influx_conf['port'], ud=n2k_conf['udp_port']))
    global client
    client = InfluxDBClient(
        host=influx_conf['host'],
        port=influx_conf['port'],
        use_udp=True,
        udp_port=n2k_conf['udp_port'])

    logger.info('Checking for InfluxDB Connectivity')
    try:
        if client.ping():
            logger.info('Connected to InfluxDB')
        else:
            logger.error('Cannot connect to InfluxDB. Check Configuration/Connectivity')
    except Exception as connect_e:
        logger.error(connect_e)
        client.close()
        sys.exit(1)
   
    try:
       read_nmea2k()
    except KeyboardInterrupt:
        print('CTRL+C pressed for script')
        analyzer_process.stdout.flush()
        analyzer_process.terminate()
        analyzer_process.wait()
        client.close()


if __name__ == '__main__':
    main()
