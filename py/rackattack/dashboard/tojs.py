from realtimewebui.tojs import *
from realtimewebui import tojs
import time

_MAXIMUM_EVENTS_BACKLOG = 50


def appendEvent(eventListID, obj):
    tojs.appendAndCycle(
        "events/%s" % eventListID, dict(time=time.time(), obj=obj), maximumSize=_MAXIMUM_EVENTS_BACKLOG)
