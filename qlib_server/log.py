# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import logging
import logging.config
import logging.handlers
from multiprocessing import Queue
from qlib.log import LogFilter

LOG_Q = Queue()

log_subprocess_config = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "queue": {
            "class": "logging.handlers.QueueHandler",
            "queue": LOG_Q,
        },
    },
    "root": {"level": "DEBUG", "handlers": ["queue"]},
}


class DispatcherHandler:
    """
    A simple handler for logging events. It runs in the listener process and
    dispatches events to loggers based on the name in the received record,
    which then get dispatched, by the logging system, to the handlers
    configured for those loggers.
    """

    def handle(self, record):
        logger = logging.getLogger(record.name)
        # The process name is transformed just to show that it's the listener
        # doing the logging to files and console
        logger.handle(record)


def listener_process(stop_event, config):
    """
    This could be done in the main process, but is just done in a separate
    process for illustrative purposes.

    This initialises logging according to the specified configuration,
    starts the listener and waits for the main process to signal completion
    via the event. The listener is then stopped, and the process exits.
    """

    logging.config.dictConfig(config)
    listener = logging.handlers.QueueListener(LOG_Q, DispatcherHandler())
    listener.start()
    stop_event.wait()
    listener.stop()
