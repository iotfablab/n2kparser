#!/usr/bin/env python3

from subprocess import Popen, PIPE
import sys
import os
import json
import threading
import time
import signal
import logging

from influxdb import InfluxDBClient


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
CONF_PATH = '/etc/umg/conf.json'

# InfluxDB Client
client = InfluxDBClient(host='localhost', port=8086, use_udp=True, udp_port=8093)

# Actisense-Serial
actisense_process = Popen(['actisense-serial', '-r', '/dev/ttymxc2'],stdout=PIPE)

# Analyzer Stream for output in JSON
analyzer_process = Popen(['analyzer', '-json'],stdin=actisense_process.stdout, stdout=PIPE, stderr=PIPE)




class ReaderThread(threading.Thread):

     def __init__(self, stream):
         threading.Thread.__init__(self)
         self.stream = stream

     def run(self):
         logger.info('Starting Stream Reading for NMEA2000')
         while True:
             line = self.stream.readline().decode('utf-8')
             if len(line) == 0:
                 logger.info('Length of incoming data is 0')
                 logger.debug(line)
                 break
             try:
                 logger.info('Parsing the incoming JSON')
                 n2k_dict = json.loads(line)
             except Exception as e:
                 logger.exception(e)
                 logger.error('Exception during Parsing of incoming JSON')
                 print(e)
                 pass
            
             global CONF
             if str(n2k_dict['pgn']) in list(CONF['pgnConfigs'].keys()):
                for each_pgn_conf in CONF['pgnConfigs'][str(n2k_dict['pgn'])]:
                    measurement = each_pgn_conf
                    code = measurement['code']
                    label = measurement['fieldLabel']
                    value = n2k_dict['fields'][label]
                    if 'source' in measurement:
                        if measurement['source'] != n2k_dict['src']:
                            break
                    #if (not 'filterCode' in measurement or measurement['filterValue'] == n2k_dict[measurement['filterCode']]) and value:
                    logger.info('Parsing data for: {}'.format(str(n2k_dict['pgn'])))
                    logger.debug({'c': measurement['code'], 'v': value, 't': time.time()})
                    db_packet = {"tags": {"type": "n2k"}, "time":time.time(), "points": [{"measurement": code, "fields": {"v": float(value), "status": 0}}]}
                    #print(db_packet)
                    logger.info('Sending data to InfluxDB')
                    try:
                        client.send_packet(db_packet)
                    except Exception as e:
                        logger.exception(e)
                        print('Error during Sending data to InfluxDB')
                        pass
                    



def main():
    with open(CONF_PATH) as cFile:
        _conf = json.load(cFile)
    global CONF
    CONF = _conf['n2k']
    reader = ReaderThread(analyzer_process.stdout)
    try:
        reader.start()
        analyzer_process.wait()
        reader.join()
    except KeyboardInterrupt:
        os.kill(os.getpid(analyzer_process.pid), signal.SIGTERM)
        os.kill(os.getpid(actisense_process.pid), signal.SIGTERM)
        logger.exception('CTRL+C Hit.')
        sys.exit(0)
    
    except Exception as e:
        logger.exception(e)
        pass


if __name__ == '__main__':
    main()
