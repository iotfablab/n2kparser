#!/usr/bin/env python3

from subprocess import Popen, PIPE
import sys
import os
import json
import threading
import time
import signal
import logging
import argparse

from influxdb import InfluxDBClient

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.FileHandler("/var/log/n2kparser.log")
handler.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s-%(name)s-%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# n2k configuration JSON file
CONF = dict()
# CONF File Path
CONF_PATH = ''

def parse_args():
    parser = argparse.ArgumentParser(description='CLI to store Actisense-NGT Gateway values to InfluxDB')
    parser.add_argument('--path', type=str, required=False, default='/etc/umg/conf.json',
                        help='Provide the path to the `conf.json` file for Script')
    return parser.parse_args()

if __name__ == '__main__':

    args = parse_args()
    CONF_PATH = args.path
    logger.debug('Conf File Path: {}'.format(CONF_PATH))
    logger.info('Reading Configuration for NMEA2000')
    with open(CONF_PATH) as cFile:
        _conf = json.load(cFile)
        CONF = _conf['n2k']
    
    # InfluxDB Client
    client = InfluxDBClient(host='localhost', port=8086, use_udp=True, udp_port=CONF['dbConf']['udp_port'])

    # Actisense-Serial
    actisense_process = Popen(['actisense-serial', '-r', CONF['port']], stdout=PIPE)

    # Analyzer Stream for output in JSON
    analyzer_process = Popen(['analyzer', '-json'], stdin=actisense_process.stdout, stdout=PIPE, stderr=PIPE)

    PGNs = list(map(int, CONF['pgnConfigs'].keys()))
    # print(PGNs)
    logger.debug('PGNs: {}'.format(PGNs))

    while True:
        incoming_json = analyzer_process.stdout.readline().decode('utf-8')
        try:
            incoming_data = json.loads(incoming_json)

            if incoming_data['pgn'] in PGNs:

                # remove unnecessary keys
                del incoming_data['dst']
                del incoming_data['prio']
                
                # empty influx json to send to DB
                influx_frame = {
                    'time': '',
                    'tags': {},
                    'points': []
                }
                
                influx_frame['time'] = incoming_data['timestamp']

                # Create a set of all available fields from the incoming frame
                incoming_fields = set(incoming_data['fields'].keys())
                fields_from_conf = set(CONF['pgnConfigs'][str(incoming_data['pgn'])]['fieldLabels'])
                logger.debug('Fields To Log: {}'.format(fields_from_conf.intersection(incoming_fields)))
                
                # Get all the Fields necessary to be stored into InfluxDB
                for selected_field in fields_from_conf.intersection(incoming_fields):
                    point = {
                        'measurement': incoming_data['description'].replace(" ", ""),
                        'fields': {}
                    }

                    if type(incoming_data['fields'][selected_field]) is not str:
                        # store numeric value as float
                        point['fields'][selected_field] = float(incoming_data['fields'][selected_field])
                    else:
                        # store it as a string
                        point['fields'][selected_field] = incoming_data['fields'][selected_field]
                        
                    point['fields']['status'] = 0.0
                    
                    influx_frame['points'].append(point)
                
                # check if the configuration for the PGN has the `fromSource` Key
                if 'fromSource' in list(CONF['pgnConfigs'][str(incoming_data['pgn'])].keys()):
                    logger.info('PGN Source Filter Check')
                    if incoming_data['src'] == CONF['pgnConfigs'][str(incoming_data['pgn'])]['fromSource']:
                        logger.info('PGN: {} with src: {}'.format(incoming_data['pgn'], incoming_data['src']))
                        client.send_packet(influx_frame)
                else:
                    client.send_packet(influx_frame)
                logger.info('Packet Sent for PGN: {}, {}'.format(incoming_data['pgn'], incoming_data['description']))

        except Exception as e:
            logger.exception(e)

        except KeyboardInterrupt:
            logger.exception('CTRL + C pressed')
            analyzer_process.stdout.flush()
            analyzer_process.terminate()
            analyzer_process.wait()