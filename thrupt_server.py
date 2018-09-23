import argparse
import os
import pdb
import random
import signal

from twisted.internet import defer, reactor, task
from twisted.internet.error import ConnectError
from twisted.web import server, resource
from twisted.web.client import Agent, ResponseFailed

from metrics import metrics


class Server(resource.Resource):
    isLeaf = True

    def returnContent(self, deferred, request, msg):
        metrics.incr("thrupt.server.requests")
        code = random.choice([200, 500])
        request.setResponseCode(code)
        print(code)
        request.write(b'hello!\n')
        request.finish()

    def cancelAnswer(self, err, request, delayedTask):
        print("canceled")
        metrics.incr("thrupt.server.canceled")
        delayedTask.cancel()

    def render_GET(self, request):
        d = defer.Deferred()
        delayedTask = reactor.callLater(1, self.returnContent, d, request, '')
        request.notifyFinish().addErrback(self.cancelAnswer, request, delayedTask)
        return server.NOT_DONE_YET


def runServer(port):
    s = server.Site(Server(), logPath='server.log')
    reactor.listenTCP(port, s)
    print(f"listening on {port}")
