import threading
from rackattack.dashboard import tojs
from rackattack import clientfactory
import time
import logging
import pymongo


class PollThread(threading.Thread):
    _INTERVAL = 5

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        threading.Thread.start(self)

    def run(self):
        while True:
            time.sleep(self._INTERVAL)
            try:
                client = clientfactory.factory()
            except:
                logging.exception("Unable to create ipc client")
                continue
            try:
                self._work(client)
            finally:
                client.close()

    def _work(self, client):
        try:
            while True:
                time.sleep(self._INTERVAL)
                status = client.call('admin__queryStatus')
                self._publish(status)
        except:
            logging.exception("Unable to query status")

    def _publish(self, status):
        tojs.set('status', status)


class InaugurationTimesPollThread(threading.Thread):
    POLL_INTERVAL = 60

    def __init__(self, databaseHost="localhost"):
        threading.Thread.__init__(self)
        self.databaseHost = databaseHost
        self._connection = None
        self._db = None
        self.daemon = True
        threading.Thread.start(self)
        logging.info("Inauguration poll thread initialized.")

    def run(self):
        while True:
            try:
                self._connection = pymongo.MongoClient(self.databaseHost)
                self._db = self._connection.rackattack_stats
            except:
                logging.exception("Unable to create database client")
                time.sleep(self.POLL_INTERVAL)
                continue
            try:
                self._work()
            finally:
                self._connection.close()
                time.sleep(self.POLL_INTERVAL)

    def getAverageInaugurationTimeBy(self, fieldName):
        pipe = [{'$match': {'inauguration_done': True}},
                {'$group': {'_id': "$%(fieldName)s" % dict(fieldName=fieldName),
                            'averageInaugurationTime': {'$avg': '$inauguration_period_length'}}},
                {'$sort': {'averageInaugurationTime': -1}}]
        data = self._db.inaugurations.aggregate(pipe)
        if isinstance(data, dict):
            data = data["result"]
        else:
            data = list(data)
        return data

    def _work(self):
        try:
            while True:
                logging.info("Querying database for inauguratio times...")
                result = dict()
                result["averageTimeByHost"] = self.getAverageInaugurationTimeBy("host_id")
                result["averageTimeByLabel"] = self.getAverageInaugurationTimeBy("imageLabel")
                print result["averageTimeByLabel"]
                self._publish(result)
                time.sleep(self.POLL_INTERVAL)
        except:
            logging.exception("Unable to query status")

    def _publish(self, data):
        tojs.set('inaugurationsStats', data)
