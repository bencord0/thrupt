import argparse
import logging
import pdb
import sys

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import Factory

from thrupt_server import runServer
from thrupt_client import runClient
from thrupt_proxy import runProxy

Factory.noisy = False

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=["proxy", "client", "server"])
parser.add_argument("--connect", default="http://localhost:8000")
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--rate", type=int, default=10)


def main():
    args = parser.parse_args()

    if args.mode == "server":
        runServer(args.port)

    elif args.mode == "client":
        runClient(args.connect, args.rate)

    elif args.mode == "proxy":
        runProxy(args.port)

    else:
        return

    log.startLogging(sys.stdout)
    reactor.run()


if __name__ == "__main__":
    main()
