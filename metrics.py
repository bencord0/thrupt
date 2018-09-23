import os

import statsd

STATSD_HOST = os.getenv("STATSD_HOST", "localhost")
STATSD_PORT = int(os.getenv("STATSD_PORT", "8125"))

metrics = statsd.StatsClient(STATSD_HOST, STATSD_PORT)
