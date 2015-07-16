import logging
import argparse
import realtimewebui.config
import os
from realtimewebui import server
from realtimewebui import rootresource
from realtimewebui import render
from rackattack.dashboard import pollthread
from twisted.web import static
from twisted.web.resource import Resource
import json
import pymongo
import datetime
import bson

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

parser = argparse.ArgumentParser()
parser.add_argument("--webPort", type=int, default=6001)
parser.add_argument("--webSocketPort", type=int, default=6002)
parser.add_argument("--realtimewebuiRoot")
parser.add_argument("--dashboardRoot")
parser.add_argument("--localhostRackattackProvider", action='store_true')
args = parser.parse_args()
connection = pymongo.MongoClient("localhost")
db = connection.rackattack_stats

if args.realtimewebuiRoot is not None:
    realtimewebui.config.REALTIMEWEBUI_ROOT_DIRECTORY = args.realtimewebuiRoot
if args.localhostRackattackProvider:
    os.environ['RACKATTACK_PROVIDER'] = \
        'tcp://localhost:1014@@amqp://guest:guest@localhost:1013/%2F@@http://localhost:1016'


class DBQuery(Resource):
    @classmethod
    def parseMongoDBResult(cls, result):
        if isinstance(result, dict):
            return result["result"]
        return list(result)

    def render_GET(self, request):
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        result = self._getResult(request)
        result = self.parseMongoDBResult(result)
        defaultValueFields = self._getFieldsInWhichToPutDefaultValues()
        if defaultValueFields is None:
            defaultValueFields = []
        unixTimestampFields = self._getUnixTimestampFields()
        if unixTimestampFields is None:
            unixTimestampFields = []
        for record in result:
            for key, value in record.iteritems():
                if isinstance(value, bson.objectid.ObjectId):
                    record[key] = str(value)
                if isinstance(value, datetime.datetime):
                    record[key] = value.isoformat()
                if key in unixTimestampFields:
                    record[key] = datetime.datetime.fromtimestamp(int(value)).strftime('%Y-%m-%d %H:%M:%S')
            for field in defaultValueFields: 
                record.setdefault(field, "unknown")
        return json.dumps(result)

    def _getResult(self):
        raise NotImplementedError
    
    def _getFieldsInWhichToPutDefaultValues(self):
        raise NotImplementedError

class GetAverageInaugurationTime(DBQuery):
    def _getResult(self, request):
        fieldName = self._getFieldName()
        pipe = [{'$match': {'inauguration_done': True}},
                {'$group': {'_id': "$%(fieldName)s" % dict(fieldName=fieldName),
                            'averageInaugurationTime': {'$avg': '$inauguration_period_length'}}},
                {'$sort': {'averageInaugurationTime': -1}}]
        data = db.inaugurations.aggregate(pipe)
        return data
    
    @classmethod
    def _getFieldName(self):
        raise NotImplementedError

    def _getFieldsInWhichToPutDefaultValues(self):
        return None

    def _getUnixTimestampFields(self):
        return None

class GetAverageInaugurationTimeByHost(GetAverageInaugurationTime):
    @classmethod
    def _getFieldName(cls):
        return "host_id"


class GetAverageInaugurationTimeByLabel(GetAverageInaugurationTime):
    @classmethod
    def _getFieldName(cls):
        return "imageLabel"


class GetFailedInaugurations(DBQuery):
    def _getResult(self, request):
        query = {'inauguration_done': False}
        data = db.inaugurations.find(query)
        return data

    def _getFieldsInWhichToPutDefaultValues(self):
        return ("user",)

    def _getUnixTimestampFields(self):
        return ("start_timestamp",)


pollThread = pollthread.PollThread()

render.addTemplateDir(os.path.join(args.dashboardRoot, 'html'))
render.DEFAULTS['title'] = "Rackattack"
render.DEFAULTS['brand'] = "Rackattack"
render.DEFAULTS['mainMenu'] = [dict(title="inaugurations", href="inaugurations.html")]
root = rootresource.rootResource()
root.putChild("js", static.File(os.path.join(args.dashboardRoot, "js")))
root.putChild("static", static.File(os.path.join(args.dashboardRoot, "static")))
root.putChild("favicon.ico", static.File(os.path.join(args.dashboardRoot, "static", "favicon.ico")))
root.putChild("inaugurations", rootresource.Renderer("inaugurations.html", {}))
root.putChild("averageInaugurationTimeByLabel", GetAverageInaugurationTimeByLabel())
root.putChild("averageInaugurationTimeByHost", GetAverageInaugurationTimeByHost())
root.putChild("failedInaugurations", GetFailedInaugurations())
server.runUnsecured(root, args.webPort, args.webSocketPort)
