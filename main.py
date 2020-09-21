# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import division
from __future__ import print_function

import yaml
import argparse
import multiprocessing

from qlib_server.config import init, LoggingConfig
from qlib.log import get_module_logger, set_log_with_config

from qlib_server.log import log_subprocess_config, listener_process

# read config for qlib-server
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", help="config file path", default="./config.yaml")

parser.add_argument(
    "-m",
    "--module",
    help="modules to run",
    nargs="+",
    choices=["request_handler", "data_processor"],
    default=["request_handler", "data_processor"],
)
ARGS = parser.parse_args()


# start qlib-server process
def main():
    LOG = get_module_logger(__file__)

    from qlib_server.request_handler import RequestHandler
    from qlib_server.data_processor import DataProcessor

    LOG.info("QLibServer starting...")
    threads = []
    if "request_handler" in ARGS.module:
        threads.append(RequestHandler())
    if "data_processor" in ARGS.module:
        threads.append(DataProcessor())

    for t in threads:
        t.start()

    for t in threads:
        t.join()


if __name__ == "__main__":
    with open(ARGS.config) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    # setting root error logger send to email
    # setting root logger to queue
    set_log_with_config(log_subprocess_config)
    logger_config = config.get("logging_config", LoggingConfig["logging_config"])
    stop_event = multiprocessing.Event()
    log_process = multiprocessing.Process(target=listener_process, args=(stop_event, logger_config))
    log_process.start()

    init(config)
    main()

    stop_event.set()
    log_process.join()
