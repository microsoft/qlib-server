# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import division
from __future__ import print_function

import time
import pickle
import threading
from packaging import version
from flask import Flask, request
from flask_socketio import SocketIO
from packaging.specifiers import SpecifierSet

from .config import C
from .utils import init_rabbitmq_channel, get_redis_connection

from qlib.log import get_module_logger

time_logger = get_module_logger("RequestHandler")


class RequestListener(threading.Thread):
    """Request listener class.

    The working procedure of this class is:

        - establish connections with clients
        - listens to requests from clients
        - get a unique task_uri for a request
        - publish the request as a task to rabbitmq
    """

    def __init__(self, socketio, app):
        super(RequestListener, self).__init__()

        # define flask app instances
        self.socketio = socketio
        self.app = app

        # define server instances
        self.channel = init_rabbitmq_channel(C.queue_host, C.queue_user, C.queue_pwd)
        self.channel.queue_declare(queue=C.task_queue, durable=True)
        self.channel.queue_declare(queue=C.message_queue, durable=True)
        self.logger = get_module_logger(self.__class__.__name__)
        self.redis_t = get_redis_connection()

    def on_connect(self):
        """Callback function when the server accepted a connection from a client."""
        time_logger.debug("Connection established at %f" % time.time())
        self.logger.info("Connection established with client %s" % request.sid)

    def on_disconnect(self):
        """Callback function when the server terminated a connection from a client."""
        time_logger.debug("Connection destructed at %f" % time.time())
        self.logger.info("Connection finished with client %s" % request.sid)

    @staticmethod
    def check_version(v):
        ver = C.client_version
        if v.lower().endswith(".dev"):
            v = v[: -4]
        if version.parse(v) not in SpecifierSet(ver):
            raise Exception("Client version mismatch, please upgrade your qlib client ({})".format(ver))

    def publish_task(self, task_type, request_body, client_ssid):
        """Publish a task to rabbitmq task_queue.

        It will first check in redis whether an identical task is being processed.
        Then the task will be published to rabbitmq if no identical task is being processed.
        The ssid of the clients that are requesting the data will be saved in redis.
        The task is published in the format as below:

        .. code-block:: pickle

            {
                'type': 'calendar'/'instrument'/'feature',
                'ssid': client session_id,
                **request_body
            }
        """
        time_logger.debug("publish task to queue at %f" % time.time())
        self.logger.info("Publish %s task to rabbitmq" % task_type)
        self.channel.basic_publish(
            exchange="",
            routing_key=C.task_queue,
            body=pickle.dumps(dict({"meta": {"type": task_type, "ssid": client_ssid}, "args": request_body})),
        )
        time_logger.debug("finish publishing task to queue at %f" % time.time())

    def publish_message(self, message_type, message_body, status_code, ssid, detailed_info=None):
        """Publish a message to rabbitmq message_queue.

        The message is published in the format as below:
        For calendar task:

        .. code-block:: pickle

            {
                'type': 'calendar',
                'ssids': client session_ids,
                'message': calendar list,
                'status': 0(success)/1(invalid data),
                'detailed_info': None
            }

        For instrument task:

        .. code-block:: pickle

            {
                'type': 'instrument',
                'ssids': client session_ids,
                'message': instrument list/dict,
                'status': 0(success)/1(invalid data)
                'detailed_info': None
            }

        For feature task:

        .. code-block:: pickle

            {
                'type': 'feature',
                'ssids': client session_ids,
                'message': uri,
                'status': 0(success)/1(invalid uri)
                'detailed_info': None
            }

        The data processor could send some detailed_info to the client
        """
        self.logger.info("Publish %s message [%s] to rabbitmq" % (message_type, str(message_body)[:200]))
        self.channel.basic_publish(
            exchange="",
            routing_key=C.message_queue,
            body=pickle.dumps(
                dict(
                    {
                        "type": message_type,
                        "data": message_body,
                        "ssids": [ssid],
                        "status": status_code,
                        "detailed_info": detailed_info,
                    }
                )
            ),
        )

    def on_calendar_request_received(self, calendar_request_body):
        """Callback function when the server received a calendar request from a client.

        Parse this request, get its task_uri and publish the task.
        The request is formatted as below:

        .. code-block:: pickle

            {
                'start_time': start_time,
                'end_time': end_time,
                'freq': freq
            }
        """
        time_logger.debug("receive request at %f" % time.time())
        body = pickle.loads(calendar_request_body["body"])
        self.logger.info("Received calendar request from client: %.200s" % body)
        try:
            self.check_version(calendar_request_body["head"]["version"])
        except Exception as e:
            self.logger.error(e)
            self.publish_message("calendar", None, 1, request.sid, str(e))
        else:
            self.publish_task("calendar", body, request.sid)

    def on_instrument_request_received(self, instrument_request_body):
        """Callback function when the server received a instrument request from a client.

        Parse this request, get its task_uri and publish the task.
        The request is formatted as below:

        .. code-block:: pickle

            {
                'instruments': instruments,
                'start_time': start_time,
                'end_time': end_time,
                'freq': freq
            }
        """
        time_logger.debug("receive request at %f" % time.time())
        body = pickle.loads(instrument_request_body["body"])
        self.logger.info("Received instrument request from client: %.200s" % body)
        try:
            self.check_version(instrument_request_body["head"]["version"])
        except Exception as e:
            self.logger.error(e)
            self.publish_message("instrument", None, 1, request.sid, str(e))
        else:
            self.publish_task("instrument", body, request.sid)

    def on_feature_request_received(self, feature_request_body):
        """Callback function when the server received a feature request from a client.

        Parse this request, get its task_uri and publish the task.
        The request is formatted as below:

        .. code-block:: pickle

            {
                'instruments': instruments,
                'fields': fields,
                'start_time': start_time,
                'end_time': end_time,
                'freq': freq
            }
        """
        time_logger.debug("receive calendar request at %f" % time.time())
        body = pickle.loads(feature_request_body["body"])
        self.logger.info("Received feature request from client: %.200s" % body)
        try:
            self.check_version(feature_request_body["head"]["version"])
        except Exception as e:
            self.logger.error(e)
            self.publish_message("feature", None, 1, request.sid, str(e))
        else:
            self.publish_task("feature", body, request.sid)

    def run(self):
        """Start the process that binds the callback functions."""
        self.logger.info("request listener module start...")

        # bind socketio callbacks
        self.socketio.on_event("connect", self.on_connect)
        self.socketio.on_event("disconnect", self.on_disconnect)
        self.socketio.on_event("calendar_request", self.on_calendar_request_received)
        self.socketio.on_event("instrument_request", self.on_instrument_request_received)
        self.socketio.on_event("feature_request", self.on_feature_request_received)
        self.socketio.run(self.app, host="0.0.0.0", port=C.flask_port)


class RequestResponder(threading.Thread):
    """Request responder class.

    The working procedure of this class is:

        - listen to messages returning from rabbitmq
        - parse the messages and get the task_uri and data requested by clients
        - get ssids of clients requested the data
        - respond those clients with the data
    """

    def __init__(self, socketio):
        super(RequestResponder, self).__init__()
        self.socketio = socketio
        self.logger = get_module_logger(self.__class__.__name__)
        self.channel = init_rabbitmq_channel(C.queue_host, C.queue_user, C.queue_pwd)

    def message_callback(self, ch, method, properties, body):
        """Callback function when a task is finished and a published message is received.

        .. note:: Rabbitmq has mechanism to make sure all task is finished correctly so
                  `ch.basic_ack(delivery_tag=method.delivery_tag)` is called to tell rabbitmq
                  the message is successfully consumed.
        """
        time_logger.debug("receive message from queue at %f" % time.time())
        mbody = pickle.loads(body)
        mtype = mbody["type"]
        mssids = mbody["ssids"]
        mdata = mbody["data"]
        mstatus = mbody["status"]
        detailed_info = mbody["detailed_info"]

        self.logger.info("Receive %s message '%.200s'" % (mtype, mbody))
        time_logger.debug("respond to clients at %f" % time.time())
        if mtype in ["calendar", "instrument", "feature"]:
            self.respond(mtype, mssids, mdata, mstatus, detailed_info)
        else:
            self.logger.warning("Unrecognized message type!")
        # mark the task as completion
        ch.basic_ack(delivery_tag=method.delivery_tag)

        time_logger.debug("finish responding to clients at %f" % time.time())

    def respond(self, message_type, client_ssids, data, status=0, detailed_info=None):
        """Respond to clients with data.

        The response is formatted as below:

        For calendar request:

        .. code-block:: pickle

            {
                'result': calendar list,
                'status': 0(success)/1(invalid data)
            }

        For instrument request:

        .. code-block:: pickle

            {
                'result': instrument list/dict,
                'status': 0(success)/1(invalid data)
            }

        For feature request:

        .. code-block:: pickle

            {
                'result': uri,
                'status': 0(success)/1(invalid uri)
            }
        """
        for ssid in client_ssids:
            # respond to all clients
            self.logger.info("Send %s response to client %s" % (message_type, ssid))
            self.socketio.emit(
                "%s_response" % message_type,
                {"result": data, "status": status, "detailed_info": detailed_info},
                room=ssid,
            )

    def run(self):
        """Start the process that listens to message_queue and respond to clients."""
        self.logger.info("request responder module start...")
        self.channel.basic_consume(on_message_callback=self.message_callback, queue=C.message_queue)
        self.channel.start_consuming()


class RequestHandler(object):
    """Request Handler class.

    Combined `RequestListener` and `RequestResponder`.
    Communicate with clients.
    """

    def __init__(self):
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, ping_interval=C.flask_ping_interval)
        self.request_listener = RequestListener(self.socketio, self.app)
        self.request_responder = RequestResponder(self.socketio)

    def start(self):
        """Start running flask service and rabbitmq publishing/consuming service."""
        self.request_listener.start()
        self.request_responder.start()

    def join(self):
        self.request_listener.join()
        self.request_responder.join()
