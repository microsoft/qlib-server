.. _build:
==============================
``Qlib-Server`` Deployment
==============================

Introduction
===================

To build a ``Qlib-Server``, user can choose:

- One-click Deployment of ``Qlib-Server``
- Step-by-step Deployment of ``Qlib-Server``


One-click Deployment
========================

One-click deployment of ``Qlib-Server`` is supported, users can choose either of the following two methods for one-click deployment:

- Deployment with ``docker-compose``
- Deployment in ``Azure``

One-click Deployment with ``docker-compose``
----------------------------------------------

Deploy ``Qlib-Server`` with docker-compose according to the following processes:

- Install ``docker``, please refer to `Docker Installation <https://docs.docker.com/engine/install>`_.
- Install ``docker-compose``, please refer to `Docker-compose Installation <https://docs.docker.com/compose/install/>`_.
- Run the following command to deploy ``Qlib-Server``:

    .. code-block:: bash

        git clone https://github.com/microsoft/qlib-server
        cd qlib-server
        sudo docker-compose -f docker_support/docker-compose.yaml --env-file docker_support/docker-compose.env build
        sudo docker-compose -f docker_support/docker-compose.yaml --env-file docker_support/docker-compose.env up -d
        # Use the following command to track the log
        sudo docker-compose -f docker_support/docker-compose.yaml --env-file docker_support/docker-compose.env logs -f


One-click Deployment in ``Azure``
--------------------------------------------

.. note:: 

    Users need to have an ``Azure`` account to deploy ``Qlib-Server`` in ``Azure``.


Deploy ``Qlib-Server`` in ``Azure`` according to the following processes:

- Install ``azure-cli``, please refer to `install-azure-cli <https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest>`_

- Add the ``Azure`` account to the configuration file ``azure_conf.yaml``

    .. code-block:: yaml

        sub_id: Your Subscription ID
        username: azure user name
        password: azure password
        # The resource group where the VM is located
        resource_group: Resource group name

- Execute the deployment script
    - Run the following command:

    .. code-block:: bash

        git clone https://github.com/microsoft/qlib-server
        cd qlib-server/scripts
        python azure_manager.py create_qlib_cs_vm \
            --qlib_server_name test_server01 \
            --qlib_client_names test_client01 \
            --admin_username test_user \
            --ssh_key_value ~/.ssh/id_rsa.pub \
            --size standard_NV6_Promo\
            --conf_path azure_conf.yaml

    - To know more about parameters, please run the following command:

    .. code-block:: bash

        python azure_manager.py create_qlib_cs_vm -- --help


Step-by-step Deployment
===========================

Users can deploy ``Qlib-Server`` step by step, which has the following processes:

- Build ``RabbitMQ``
- Build ``Redis``
- Build ``NFS``
- Build ``Qlib-Server``

Build ``RabbitMQ``
----------------------

``RabbitMQ`` is a general task queue that enables qlib-server to separate request handling process and data generating process.

.. note:: Users need not to  build ``RabbitMQ`` instance on the same server as ``Qlib-Server``.

Build ``RabbitMQ`` according to the following processes:

- Import ``RabbitMQ`` signing key on your system:

    .. code-block:: bash

        echo 'deb http://www.rabbitmq.com/debian/ testing main' | sudo tee /etc/apt/sources.list.d/rabbitmq.list
        wget -O- https://www.rabbitmq.com/rabbitmq-release-signing-key.asc | sudo apt-key add -

- Update apt cache and install ``RabbitMQ`` server on your system:

    .. code-block:: bash

        sudo apt-get update
        sudo apt-get install rabbitmq-server

- Enable the ``RabbitMQ service`` and start it.

    .. code-block:: bash

        # Using Init –
        sudo update-rc.d rabbitmq-server defaults
        sudo service rabbitmq-server start
        sudo service rabbitmq-server stop

        # Using Systemctl -
        sudo systemctl enable rabbitmq-server
        sudo systemctl start rabbitmq-server
        sudo systemctl stop rabbitmq-server

- Create admin user in ``RabbitMQBy``
    By default ``RabbitMQBy`` creates a username `guest` with password `guest`. Users can also create admin user in RabbitMQ:

    .. code-block:: bash

        sudo rabbitmqctl add_user admin <your password>
        sudo rabbitmqctl set_user_tags admin administrator
        sudo rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"


- Enable web management console
    ``RabbitMQ`` also provides and web management console for managing the entire ``RabbitMQ``. To enable web management console run following command. The web management console helps users with managing ``RabbitMQ`` server.

    .. code-block:: bash

        sudo rabbitmq-plugins enable rabbitmq_management

    Visit `<your rabbitmq host>:15672` to manage your queue. Keep in mind your rabbitmq host and credentials. It will be used in qlib-server config.


Build ``Redis``
----------------------

``Qlib-Server`` needs ``redis`` to store and read some meta info as well as thread lock.

.. note:: Users need not to build redis instance on the same server as ``Qlib-Server``.

Build ``redis`` according to the following processes:

- Download the latest version of redis and install
    .. code-block:: bash

        mkdir ~/redis
        cd ~/redis
        wget http://download.redis.io/releases/redis-5.0.4.tar.gz
        tar -zxvf redis-5.0.4.tar.gz
        cd redis-5.0.4
        sudo make && make install

- Start redis service
    .. code-block:: bash

        /usr/local/bin/redis-server

    The default port of redis is **6379**. Keep in mind your redis host and port. It will be used in qlib-server config.


Build ``NFS``
----------------------

Before starting ``Qlib-Server``, it's necessary to make sure the cache file directories are mounted (or at least ready to be mounted) to clients by configuring nfs service.

Build ``NFS`` according to the following processes:

- Install NFS service:

    .. code-block:: bash

        sudo apt-get install nfs-kernel-server

- Check if the nfs port is open:
    .. code-block:: bash

        netstat -tl

    .. note:: 

        By seeing ``tcp   0   0 *:nfs   *:*    LISTEN``, the nfs port is ready for listening. Restart the service to ensure it can be used:

        .. code-block:: bash

            sudo /etc/init.d/nfs-kernel-server restart

- Modify ``/etc/exports`` to give the directories ability to be mounted. To find out how the keywords like `rw` work and change them, please refer to nfs documents.

.. code-block:: bash

    sudo echo '<your data directory> *(rw,sync,no_subtree_check,no_root_squash)'>>/etc/exports


Use `showmount` to view the exported directories.


Build ``Qlib-Server``
----------------------

Users can choose one of the following two methods to build ``Qlib-Server``:

- Build with Source Code
- Build with Dockerfile

Build with Source Code
~~~~~~~~~~~~~~~~~~~~~~~~~

Build ``Qlib-Server`` with source code according to the following processes:

- Enter the ``Qlib-Server`` directory and run `python setup.py install`. 
- Modify the config.yaml according to users' needs and configs. 
- Start using ``Qlib-server`` by running:
    .. code-block:: bash

        cp config_template.yaml config.yaml
        edit config.yaml  # Please edit the server config.
        python main.py -c config.yaml
	
.. warning::
	
    Rabbitmq and redis configurations cannot be shared among multiple qlib-server instances
    
    Eg:

    .. code-block:: bash
        
        In config_1.yaml, redis_db:1 task_queue: 'task_queue_1' √
        In config_2.yaml, redis_db:2 task_queue: 'task_queue_2' √
        ---------------------------------------------------------
        In config_1.yaml, redis_db:1 task_queue: 'task_queue_1' ×
        In config_2.yaml, redis_db:1 task_queue: 'task_queue_1' ×

.. note:: 

    The content of config.yaml is as follows

    .. code-block::

        provider_uri: <QLIB_DATA>
        flask_server: <FLASK_SERVER_HOST>
        flask_port: 9710
        queue_host: <QUEUE_HOST>
        queue_user: <QUEUE_USER>
        queue_pwd: <QUEUE_PASS>
        task_queue: 'task_queue'
        message_queue: 'message_queue'
        max_concurrency: 10
        max_process: 10
        redis_host: <REDIS_HOST>
        redis_port: 6379
        redis_task_db: 1
        auto_update: 0
        update_time: '23:45'
        client_version: '>=0.4.0'
        server_version: '>=0.4.0'
        dataset_cache_dir_name: dataset_cache
        features_cache_dir_name: features_cache
        logging_level: INFO
        logging_config:
            version: 1
            formatters:
                logger_format:
                format: '[%(process)s:%(threadName)s](%(asctime)s) %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s'

            filters:
                mail_filter:
                (): qlib_server.log.LogFilter
                param:
                    - '.*?WARN: data not found for.*?'

            handlers:
                console:
                class: logging.StreamHandler
                level: DEBUG
                formatter: logger_format

                file:
                class: logging.FileHandler
                mode: w
                filename: qlib_server.log
                level: INFO
                formatter: logger_format

                others:
                class: logging.StreamHandler
                level: WARNING
                formatter: logger_format

                other_file:
                class: logging.FileHandler
                mode: w
                filename: qlib_server_other_module.log
                level: WARNING
                formatter: logger_format
            loggers:
                qlib:
                level: DEBUG
                handlers:
                    - console
            root:
                handlers:
                - others
    
    - `provider_uri`
        ``Qlib`` data directory
    - `flask_server`
        Flask server host/ip, can be ``0.0.0.0`` or ``private ip``
    - `flask_port`
        Data service port, with which the client port must be consistent to access server
    - `queue_host`
        ``RabbitMQ`` server ip/host
    - `queue_user`
        ``RabbitMQ`` user name
    - `queue_pwd`
        ``RabbitMQ`` password
    - `task_queue`
        Task queue of ``Qlib-Server``, if rabbitmq serves multiple ``Qlib-Server`` s, this value cannot be repeated
    - `message_queue`
        Message queue of ``Qlib-Server``, if rabbitmq serves multiple ``Qlib-Server`` s, this value cannot be repeated
    - `redis_host`
        ``Redis`` server host/ip
    - `redis_port`
        ``Redis`` server port
    - `redis_task_db`
        ``Redis`` database name
    - `auto_update`
        Currently, this parameter is not used
    - `update_time`
        Currently, this parameter is not used
    -  `client_version`
        The version of ``Qlib`` must be newer than `client_version` to access the ``Qlib-Server``
    - `server_version`
        The version of ``Qlib`` must be newer than `server_version` to install or run ``Qlib-Server``
    - `dataset_cache_dir_name`
        The name of the dataset cache directory, it is not recommended to modify
    - `features_cache_dir_name`
        The name of the features cache directory, it is not recommended to modify
    - `logging_level`
        Level control of ``Qlib-Server`` log
    - `logging_config`
        Log configuration, it is not recommended to modify

Build from Dockerfile
~~~~~~~~~~~~~~~~~~~~~~~~

Build ``Qlib-Server`` with Dockerfile according to the following processes:

- Install ``docker``, please refer to `Docker Installation <https://docs.docker.com/engine/install>`_.
- Start using ``Qlib-Server`` by running:
    
    .. code-block:: bash

        git clone https://github.com/microsoft/qlib-server
        cd qlib-server
        sudo docker build -f docker_support/Dockerfile -t qlib-server \
            --build-arg QLIB_DATA=/data/stock_data/qlib_data \
                QUEUE_HOST=rabbitmq_server \
                QUEUE_USER=rabbitmq_user \
                QUEUE_PASS=rebbitmq_password \
                MESSAGE_QUEUE=message_queue \
                TASK_QUEUE=task_queue \
                REDIS_HOST=redis_server \
                REDIS_PORT=6379\
                REDIS_DB=1
                FLASK_SERVER_HOST=127.0.0.1 \
                QLIB_CODE=/code\
        sudo docker run -p 9710:9710 qlib-server

