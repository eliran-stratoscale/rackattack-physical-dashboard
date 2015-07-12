import logging
import argparse
import realtimewebui.config
import os
from realtimewebui import server
from realtimewebui import rootresource
from realtimewebui import render
from rackattack.dashboard import pollthread
from twisted.web import static

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

parser = argparse.ArgumentParser()
parser.add_argument("--webPort", type=int, default=6001)
parser.add_argument("--webSocketPort", type=int, default=6002)
parser.add_argument("--realtimewebuiRoot")
parser.add_argument("--dashboardRoot")
parser.add_argument("--localhostRackattackProvider", action='store_true')
args = parser.parse_args()

if args.realtimewebuiRoot is not None:
    realtimewebui.config.REALTIMEWEBUI_ROOT_DIRECTORY = args.realtimewebuiRoot
if args.localhostRackattackProvider:
    os.environ['RACKATTACK_PROVIDER'] = \
        'tcp://localhost:1014@@amqp://guest:guest@localhost:1013/%2F@@http://localhost:1016'


hostsStatsPoller = pollthread.PollThread()
inaugurationTimePoller = pollthread.InaugurationTimesPollThread()

render.addTemplateDir(os.path.join(args.dashboardRoot, 'html'))
render.DEFAULTS['title'] = "Rackattack"
render.DEFAULTS['brand'] = "Rackattack"
render.DEFAULTS['mainMenu'] = [dict(title="inaugurations", href="inaugurations.html")]
root = rootresource.rootResource()
root.putChild("js", static.File(os.path.join(args.dashboardRoot, "js")))
root.putChild("static", static.File(os.path.join(args.dashboardRoot, "static")))
root.putChild("favicon.ico", static.File(os.path.join(args.dashboardRoot, "static", "favicon.ico")))
root.putChild("inaugurations", rootresource.Renderer("inaugurations.html", {}))
server.runUnsecured(root, args.webPort, args.webSocketPort)
