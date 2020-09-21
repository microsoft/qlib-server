# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.


from __future__ import division
from __future__ import print_function

import json
import pika
import redis
import hashlib
import redis_lock

from .config import C


# ################### Server ####################


def get_redis_connection():
    """get redis connection instance."""
    return redis.StrictRedis(host=C.redis_host, port=C.redis_port, db=C.redis_task_db)


def init_rabbitmq_channel(host, user, pwd):
    """init rabbitmq channel for task distribution."""
    user_pwd = pika.PlainCredentials(user, pwd)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host, credentials=user_pwd, heartbeat=0))
    channel = connection.channel()
    return channel


def add_to_task_l_and_check_qlen(task_uri, ssid):
    """
    Add the ssid to the task list and return the qlen after add the ssid

    we use redis database to make sure two identical tasks won't be pushed to rabbitmq repeatedly.
    instead, different clients that propose the same request will be stored and responsed together
    here we use a third-party lib : https://pypi.org/project/python-redis-lock/

    :param task_uri:
    """
    redis_t = get_redis_connection()
    with redis_lock.Lock(redis_t, "task-%s" % task_uri):
        # use list structure in redis
        # NOTE: When using list in redis, the results popped from the list is byte format.
        # The client_ssid must be transformed to str.
        redis_t.lpush(task_uri, ssid)
        return redis_t.llen(task_uri)


def pop_ssids_from_redis(task_uri):
    """get a task from redis database.

    get all clients that propose a certain request and respond to them
    """
    redis_t = get_redis_connection()
    with redis_lock.Lock(redis_t, "task-%s" % task_uri):
        client_ssid_b_list = redis_t.lrange(task_uri, 0, -1)
        redis_t.delete(task_uri)
        client_ssid_list = [ssid.decode() for ssid in client_ssid_b_list]
    return client_ssid_list


# data ####################


# ################### Other ####################
def get_task_uri(task_type, task_body):
    if task_type == "calendar":
        return hash_args(task_body)
    elif task_type == "instrument":
        return hash_args(task_body)
    elif task_type == "feature":
        if isinstance(task_body["instruments"], tuple) or isinstance(task_body["instruments"], list):
            instruments = sorted(list(task_body["instruments"]))
        else:
            if "market" in task_body["instruments"]:
                instruments = task_body["instruments"]
            else:
                instruments = {k: sorted(v) for k, v in task_body["instruments"].items()}
        fields = sorted(list([str(field).lower() for field in task_body["fields"]]))
        return hash_args(instruments, fields, task_body["freq"].lower())


def hash_args(*args):
    # json.dumps will keep the dict keys always sorted.
    string = json.dumps(args, sort_keys=True, default=str)  # frozenset
    return hashlib.md5(string.encode()).hexdigest()
