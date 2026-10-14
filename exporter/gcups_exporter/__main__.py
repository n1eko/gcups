"""Entry point: python -m gcups_exporter"""
import logging
import signal
import sys
import threading

from prometheus_client import REGISTRY, start_http_server

from .client import GcupsClient
from .collector import GcupsCollector
from .config import Config, ConfigError

log = logging.getLogger("gcups_exporter")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        config = Config.from_env()
    except ConfigError as e:
        log.error("%s", e)
        return 1

    client = GcupsClient(config.gcups_url, config.gcups_password, config.timeout_seconds)
    REGISTRY.register(GcupsCollector(client))
    start_http_server(config.port)
    log.info("listening on :%d, reading %s", config.port, config.gcups_url)

    # As PID 1 in a container, Python ignores SIGTERM unless it handles it.
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    stop.wait()
    log.info("shutting down")
    return 0


if __name__ == "__main__":
    sys.exit(main())
