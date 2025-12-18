# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import division
from __future__ import print_function

import time
import json
import threading
import multiprocessing

from .config import C
from .utils import init_rabbitmq_channel, add_to_task_l_and_check_qlen, pop_ssids_from_redis

from qlib.data import D
from qlib.data.cache import CacheUtils
from qlib.log import get_module_logger


class DataProcessor(threading.Thread):
    def __init__(self):
        super(DataProcessor, self).__init__()
        self.logger = get_module_logger(self.__class__.__name__)

    # Because the rabbitmq channel is not threading-safe.
    # We have to split the channels into different channel.
    @staticmethod
    def get_task_channel(prefetch_count=1):
        _task_channel = init_rabbitmq_channel(C.queue_host, C.queue_user, C.queue_pwd)
        _task_channel.queue_declare(queue=C.task_queue, durable=True)
        _task_channel.basic_qos(prefetch_count=prefetch_count)

        return _task_channel

    @property
    def msg_channel(self):
        # The initialization of the msg_channel is postponed after the child processes are initialized
        # So the channels will not be shared between different processes.
        if not hasattr(self, "_msg_channel"):
            self._msg_channel = init_rabbitmq_channel(C.queue_host, C.queue_user, C.queue_pwd)
            self._msg_channel.queue_declare(queue=C.message_queue, durable=True)
            self._msg_channel.basic_qos(prefetch_count=C.max_concurrency)
        return self._msg_channel

    def publish_message(self, message_type, message_body, status_code, task_uri, detailed_info=None):
        """Publish a message to rabbitmq message_queue.

        The message is published in the format as below:
        For calendar task:

        .. code-block:: json

            {
                'type': 'calendar',
                'ssids': client session_ids,
                'message': calendar list,
                'status': 0(success)/1(invalid data),
                'detailed_info': None
            }

        For instrument task:

        .. code-block:: json

            {
                'type': 'instrument',
                'ssids': client session_ids,
                'message': instrument list/dict,
                'status': 0(success)/1(invalid data)
                'detailed_info': None
            }

        For feature task:

        .. code-block:: json

            {
                'type': 'feature',
                'ssids': client session_ids,
                'message': uri,
                'status': 0(success)/1(invalid uri)
                'detailed_info': None
            }

        The data processor could send some detailed_info to the client
        """
        ssids = pop_ssids_from_redis(task_uri)

        self.logger.info("Publish %s message [%s] to rabbitmq" % (message_type, str(message_body)[:200]))
        self.msg_channel.basic_publish(
            exchange="",
            routing_key=C.message_queue,
            body=json.dumps(
                dict(
                    {
                        "type": message_type,
                        "data": message_body,
                        "ssids": ssids,
                        "status": status_code,
                        "detailed_info": detailed_info,
                    }
                )
            ),
        )

    @staticmethod
    def clear_task(body):
        """Callback function when initialize rabbitmq."""
        tbody = json.loads(body.decode("utf-8"))
        ttype = tbody["meta"]["type"]
        task_uri = D._uri(ttype, **(tbody["args"]))
        # delete task
        pop_ssids_from_redis(task_uri)

    def task_callback(self, ch, method, properties, body):
        """Callback function when a published task is received.

        When a published task is received from rabbitmq,
        a new process will be established to attend to the task.
        `self.channel.basic_qos(prefetch_count=1)` is used to control the maximum concurrency of data processing process.
        """
        self.logger.debug("Receive task from queue at %f" % time.time())
        tbody = json.loads(body.decode("utf-8"))
        ttype = tbody["meta"]["type"]
        ssid = tbody["meta"]["ssid"]
        self.logger.info("receive %s task : '%.200s'" % (ttype, tbody))

        task_uri = D._uri(ttype, **(tbody["args"]))
        self.logger.debug("check task  at %f" % time.time())
        qlen = add_to_task_l_and_check_qlen(task_uri, ssid)
        if qlen == 1:  # first to create the task queue
            # no task is running
            # here the data processes will not use the historical memory cache as before
            # acutally the memory cache is used for accelerate the inside of a
            # process

            self.logger.debug("start processing data at %f" % time.time())
            # In order to no longer clear the MemoryCache, a process has been created here.
            p = multiprocessing.Process(target=getattr(self, "%s_callback" % ttype), args=(tbody["args"], task_uri))
            p.start()
            p.join()
        else:
            self.logger.debug(f"There has already been the same task. Just append the ssid {ssid}.")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def calendar_callback(self, cbody, task_uri):
        """Target function for the established process when the received task asks for calendar data.

        Call the data provider to acquire data and publish the calendar data.
        """

        start_time = cbody["start_time"]
        end_time = cbody["end_time"]
        if start_time == "None":
            start_time = None
        if end_time == "None":
            end_time = None
        freq = cbody["freq"]
        future = cbody.get("future", False)
        status_code = 0
        self.logger.debug("process calendar data at %f" % time.time())
        try:
            calendar_result = D.calendar(start_time, end_time, freq, future)
            calendar_result = [str(c) for c in calendar_result]
            self.logger.debug("finish processing calendar data and publish message at %f" % time.time())
            self.publish_message("calendar", calendar_result, status_code, task_uri)
        except Exception as e:
            self.logger.exception(f"Error while processing request %.200s" % e)
            self.publish_message("calendar", None, 1, task_uri, str(e))

    def instrument_callback(self, ibody, task_uri):
        """Target function for the established process when the received task asks for instrument data.

        Call the data provider to acquire data and publish the instrument data.
        """

        instruments = ibody["instruments"]
        start_time = ibody["start_time"]
        end_time = ibody["end_time"]
        if start_time == "None":
            start_time = None
        if end_time == "None":
            end_time = None
        freq = ibody["freq"]
        as_list = ibody["as_list"]
        status_code = 0
        # TODO: add exceptions detection and modify status_code
        self.logger.debug("process instrument data at %f" % time.time())
        try:
            instrument_result = D.list_instruments(instruments, start_time, end_time, freq, as_list)
            if isinstance(instrument_result, dict):
                instrument_result = {i: [(str(s), str(e)) for s, e in t] for i, t in instrument_result.items()}
            self.logger.debug("finish processing instrument data and publish message at %f" % time.time())
            self.publish_message("instrument", instrument_result, status_code, task_uri)
        except Exception as e:
            self.logger.exception(f"Error while processing request %.200s" % e)
            self.publish_message("instrument", None, 1, task_uri, str(e))

    def feature_callback(self, obj, task_uri):
        """Target function for the established process when the received task asks for feature data.

        Call the data provider to acquire data and publish the feature uri.

        .. note:: it only publish the cached file uri instead of the real dataset.
        """

        instruments = obj["instruments"]
        fields = obj["fields"]
        start_time = obj["start_time"]
        end_time = obj["end_time"]
        disk_cache = int(obj.get("disk_cache", 1))
        if start_time == "None":
            start_time = None
        if end_time == "None":
            end_time = None
        freq = obj["freq"]

        status_code = 0
        self.logger.debug("process feature data at %f" % time.time())

        if not hasattr(D, "features_uri"):
            msg = "Your dataset cache mechanism doesn't have `_dataset_uri` method."
            self.logger.error(msg)
            raise AttributeError(msg)
        try:
            uri = D.features_uri(
                instruments=instruments,
                fields=fields,
                start_time=start_time,
                end_time=end_time,
                freq=freq,
                disk_cache=disk_cache,
            )
            self.logger.debug("finish processing feature data and publish message at %f" % time.time())
            self.publish_message("feature", uri, status_code, task_uri)
        except Exception as e:
            self.logger.exception(f"Error while processing request %.200s" % e)
            self.publish_message("feature", None, 1, task_uri, str(e))

    def start_consuming(self):
        """Start consuming"""
        _task_channel = self.get_task_channel(prefetch_count=1)
        _task_channel.basic_consume(on_message_callback=self.task_callback, queue=C.task_queue)
        try:
            _task_channel.start_consuming()
        except KeyboardInterrupt:
            _task_channel.close()

    def run(self):
        """Start the process that consumes tasks and process data."""
        CacheUtils.reset_lock()
        task_channel = self.get_task_channel(C.max_concurrency)
        for method, properties, body in task_channel.consume(C.task_queue, inactivity_timeout=C.inactivity_timeout):
            # if server crashes with some remaining tasks, when the server restarts this process
            # will clear the remaining tasks.
            # with inactivity_timeout, if no remaining messages exist the consume() function will
            # return a package of which the body is None.
            if body is None:
                break
            self.logger.info("clear old tasks...")
            self.clear_task(body)
            task_channel.basic_ack(method.delivery_tag)
            if task_channel.get_waiting_message_count() == 0:
                break
        task_channel.cancel()

        self.logger.info("data processor module start...")

        p_list = []
        for i in range(C.max_process):
            p_list.append(multiprocessing.Process(target=self.start_consuming, args=()))

        for p in p_list:
            p.start()

        for p in p_list:
            p.join()
