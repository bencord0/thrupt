import pdb

from twisted.internet import defer, reactor, task
from twisted.internet.error import ConnectError
from twisted.web import server, resource
from twisted.web.client import Agent, HTTPConnectionPool, ResponseFailed


class Breaker(object):

    def __init__(self):
        self._is_open = False
        self._is_half_open = False
        self._failure_count = 0
        self._failure_limit = 5
        self._success_count = 0
        self._success_limit = 5

    @property
    def isOpen(self):
        return self._is_open

    @property
    def isClosed(self):
        return not self._is_open and not self._is_half_open

    @property
    def isHalfOpen(self):
        return self._is_half_open

    def shouldTry(self):
        if self.isHalfOpen:
            return True

        if self.isOpen:
            return False

        return True

    def openCircuit(self):
        print("open")
        self._is_open = True
        self._is_half_open = False
        reactor.callLater(5, self.halfOpenCircuit)

    def halfOpenCircuit(self):
        # can only transition from open to half-open
        if not self.isOpen:
            return

        self._success_count = 0

        print("half open")
        self._is_open = True
        self._is_half_open = True

    def closeCircuit(self):
        # can only transition from half-open to closed
        if not self.isHalfOpen:
            return

        print("close")
        self._is_open = False
        self._is_half_open = False
        self._failure_count = 0

    def good(self, *_):
        self._failure_count = 0

        if self.isHalfOpen:
            self._success_count += 1

        if self._success_count >= self._success_limit:
            self.closeCircuit()

    def bad(self, *_):
        if self.isHalfOpen:
            self.openCircuit()
            return

        self._failure_count += 1

        def _decrement_failure_count():
            if self._failure_count > 0:
                self._failure_count -= 1
        reactor.callLater(1, _decrement_failure_count)

        if self._failure_count >= self._failure_limit:
            if self.isClosed:
                self.openCircuit()


class Proxy(resource.Resource):
    isLeaf = True

    def __init__(self):
        self.b = Breaker()

        pool = HTTPConnectionPool(reactor)
        self.ua = Agent(
            reactor,
            connectTimeout=0.25,
            pool=pool,
        )

    def render(self, request):

        if not self.b.shouldTry():
            request.setResponseCode(502)
            request.finish()
            return server.NOT_DONE_YET

        d = self.ua.request(request.method, request.uri)
        d.addCallbacks(
            self.handle_response, self.handle_connect_failure,
            callbackArgs=[request],
            errbackArgs=[request]
        )
        d.addErrback(self.handle_runtime_failure)

        return server.NOT_DONE_YET

    def handle_response(self, response, request):
            print("-", end="")
            # client disconnected, give up.
            if request._disconnected:
                return

            self.b.good()
            request.setResponseCode(response.code)
            for k, v in response.headers.getAllRawHeaders():
                if isinstance(v, list):
                    for _v in v:
                        request.setHeader(k, _v)
                else:
                    request.setHeader(k, v)
            response.deliverBody(self.proxyResponseToRequest(request))

    def proxyResponseToRequest(self, request):
        class ProxyResponse:
            def dataReceived(data):
                request.write(data)

            def connectionLost(failure):
                request.finish()

            def makeConnection(transport):
                pass

            def connectionMade(self):
                pdb.set_trace()
                pass

        return ProxyResponse

    def handle_connect_failure(self, failure, request):
            self.b.bad()
            print("o", end="")
            if request._disconnected:
                return

            request.setResponseCode(502)
            request.finish()

    def handle_runtime_failure(self, failure):
        print(failure)
        pdb.set_trace()
        reactor.stop()


def runProxy(port):
    s = server.Site(Proxy(), logPath='proxy.log')
    reactor.listenTCP(port, s, backlog=1)
    print(f"listening on {port}")
