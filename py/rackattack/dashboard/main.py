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


def getAverageInaugurationTimeBy(fieldName):
    pipe = [{'$match': {'inauguration_done': True}},
            {'$group': {'_id': "$%(fieldName)s" % dict(fieldName=fieldName),
                        'averageInaugurationTime': {'$avg': '$inauguration_period_length'}}},
            {'$sort': {'averageInaugurationTime': -1}}]
    data = db.inaugurations.aggregate(pipe)
    if isinstance(data, dict):
        data = data["result"]
    else:
        data = list(data)
    return data


class Query(Resource):
    def render_GET(self, request):
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        if "by" in request.args:
            groupByField = request.args["by"]
            try:
                groupByField = groupByField[0]
                groupByField = dict(host="host_id", label="imageLabel")[groupByField]
            except (IndexError, KeyError) as ex:
                logging.warn("Got a request with an invalid 'by' field")
                raise
        else:
            logging.warn("Got a request with an invalid 'by' field")
            raise ValueError("Missing 'by' field (host/label)")
        result = getAverageInaugurationTimeBy(groupByField)
        return json.dumps(result)

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
root.putChild("averageInaugurationTime", Query())
server.runUnsecured(root, args.webPort, args.webSocketPort)
