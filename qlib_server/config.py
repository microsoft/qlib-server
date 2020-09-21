# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import qlib

# TODO: fix the default config to common settings while releasing.
_server_config = {
    # flask port
    "flask_server": "172.23.233.89",
    "flask_port": 9710,
    "flask_ping_interval": 1.0,
    # rabitmq server
    "queue_host": "10.150.144.154",
    "queue_user": "guest",
    "queue_pwd": "guest",
    "task_queue": "my_task_queue",
    "message_queue": "my_message_queue",
    "max_process": 10,
    "max_concurrency": 10,
    "inactivity_timeout": 5,
    # cache update
    "auto_update": False,
    "update_time": "23:45",
    # support qlib version
    "client_version": ">=0.4.0",
    # logging
    "logging_level": "DEBUG",
    # provider_uri
    "provider_uri": "/data1/csdesign",
    # cache dir name
    "dataset_cache_dir_name": "dataset_cache",
    "features_cache_dir_name": "features_cache",
    # redis
    "redis_host": "10.150.144.154",
    "redis_port": 6379,
    "redis_task_db": 1,
}

LoggingConfig = {
    "logging_config": {
        "version": 1,
        "formatters": {
            "logger_format": {
                "format": "[%(process)s:%(threadName)s](%(asctime)s) %(levelname)s - "
                "%(name)s - [%(filename)s:%(lineno)d] - %(message)s"
            }
        },
        "filters": {"log_filter": {"()": "qlib_server.log.LogFilter", "param": [".*?WARN: data not found for.*?"]}},
        "handlers": {
            "console": {"class": "logging.StreamHandler", "level": "DEBUG", "formatter": "logger_format"},
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "mode": "w",
                "filename": "qlib_server.log",
                "formatter": "logger_format",
            },
            "others": {"class": "logging.StreamHandler", "level": "WARNING", "formatter": "logger_format"},
            "other_file": {
                "class": "logging.FileHandler",
                "level": "WARNING",
                "mode": "w",
                "filename": "qlib_server_other_module.log",
                "formatter": "logger_format",
            },
        },
        "loggers": {
            "qlib": {
                "level": "DEBUG",
                "handlers": [
                    "console",
                    # 'file'
                ],
            }
        },
        "root": {
            "handlers": [
                "others",
                # 'other_file'
            ]
        },
    }
}

_default_config = dict(_server_config, **LoggingConfig)


class Config:
    def __getitem__(self, key):
        return _default_config[key]

    def __getattr__(self, attr):
        try:
            return _default_config[attr]
        except KeyError:
            raise AttributeError(f"No attr name {attr}")

    def __setitem__(self, key, value):
        _default_config[key] = value

    def __setattr__(self, attr, value):
        _default_config[attr] = value


# global config
C = Config()


def init(conf, logging_config=None):
    """set_config

    :param conf: A  dict-like object
    :param logging_config: logging config
    """
    # config the files
    for key, val in conf.items():
        C[key] = val
    qlib.init(
        "server",
        provider_uri=C["provider_uri"],
        logging_level=C["logging_level"],
        logging_config=logging_config,
        dataset_cache_dir_name=C["dataset_cache_dir_name"],
        features_cache_dir_name=C["features_cache_dir_name"],
        redis_task_db=C["redis_task_db"],
        redis_port=C["redis_port"],
        redis_host=C["redis_host"],
    )
