#!/usr/bin/env python3

from subprocess import Popen, PIPE
import sys
import os
import json
import threading
import time
import signal
from influxdb import InfluxDBClient

CONF = dict()

client = InfluxDBClient(host='localhost', port=8086, use_udp=True, udp_port=8093)

actisense_process = Popen(['actisense-serial', '-r', '/dev/ttymxc2'],stdout=PIPE)

analyzer_process = Popen(['analyzer', '-json'],stdin=actisense_process.stdout, stdout=PIPE, stderr=PIPE)


class ReaderThread(threading.Thread):

     def __init__(self, stream):
         threading.Thread.__init__(self)
         self.stream = stream

     def run(self):
         while True:
             line = self.stream.readline().decode('utf-8')
             if len(line) == 0:
                 break
             try:
                 n2k_dict = json.loads(line)
             except Exception as e:
                 raise(e)
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
                     print({'c': measurement['code'], 'v': value, 't': time.time()})
                     db_packet = {"tags": {"type": "n2k"}, "time":time.time(), "points": [{"measurement": code, "fields": {"v": value, "status": 0}}]}
                     #print(db_packet)
                     client.send_packet(db_packet)



def main():
    reader = ReaderThread(analyzer_process.stdout)
    try:
        reader.start()

        analyzer_process.wait()
        reader.join()
    except Exception as e:
        os.kill(os.getpid(analyzer_process.pid), signal.SIGTERM)
        os.kill(os.getpid(actisense_process.pid), signal.SIGTERM)
        raise(e)

if __name__ == '__main__':

    with open('/etc/umg/conf.json') as cFile:
        _conf = json.load(cFile)
    CONF = _conf['n2k']
    main()
