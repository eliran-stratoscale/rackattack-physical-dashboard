import threading
from rackattack.dashboard import tojs
from rackattack import clientfactory
import time
import logging


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
