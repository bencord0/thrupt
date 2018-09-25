import os
import pdb
import signal

from furl import furl

from twisted.internet import defer, reactor, task
from twisted.internet.endpoints import HostnameEndpoint
from twisted.internet.error import ConnectError
from twisted.logger import Logger
from twisted.web.client import Agent, ProxyAgent, ResponseFailed

from metrics import metrics


class Client(object):
    def __init__(self, connect, ua):
        self.connect = connect
        self.ua = ua
        self.log = Logger()

    def request_GET(self):
        metrics.incr("thrupt.client.requests")
        d = self.ua.request(b'GET', self.connect.encode())
        d.addCallbacks(self.handle_response, self.handle_connect_error)
        d.addBoth(self.handle_errors)

    def handle_response(self, response):
        code_char = "-" if response.code < 300 else "="
        self.log.info(code_char, end="")
        metrics.incr(f"thrupt.client.{response.code}")

    def handle_connect_error(self, failure):
        if issubclass(failure.type, ConnectError):
            self.log.info("o", end="")
            return

        # This is a bug in the proxy
        if issubclass(failure.type, ResponseFailed):
            self.log.info("x", end="")
            return

        # New kind of error, stop and debug
        reactor.stop()
        pdb.set_trace()

    def handle_errors(self, failure):
        if failure is None:
            return

        # This is a bug in the proxy
        if issubclass(failure.type, ResponseFailed):
            self.log.info("x", end="")
            return

        reactor.stop()
        pdb.set_trace()


def runClient(connect, rate):
    http_proxy = os.getenv('HTTP_PROXY')
    if http_proxy:
        http_proxy = furl(http_proxy)
        ep = HostnameEndpoint(reactor, http_proxy.host, http_proxy.port)
        ua = ProxyAgent(ep)
    else:
        ua = Agent(reactor)
    client = Client(connect, ua)
    looper = task.LoopingCall(client.request_GET)

    # register signal handler to stop the looping call
    def signal_handler(signal, frame):
        looper.stop()
        reactor.runUntilCurrent()
        reactor.stop()
    signal.signal(signal.SIGINT, signal_handler)

    looper.start(1 / rate)
