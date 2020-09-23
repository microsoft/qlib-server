
=================================================
Using ``Qlib`` in ``Online`` Mode
=================================================

Introduction
================
In the `Qlib Document <https://qlib.readthedocs.io/en/latest>`_, the ``Offline`` mode has been introduced. In addition to ``offline`` mode, users can use ``Qlib`` in ``Online`` mode.

The ``Online`` mode is designed to solve the following problems:

- Manage the data in a centralized way. Users don't have to manage data of different versions.
- Reduce the amount of cache to be generated.
- Make the data can be accessed in a remote way.

In ``Online`` mode, the data provided for ``Qlib`` will be managed in a centralized manner by ``Qlib-Server``.

Using ``Qlib`` in ``Online`` Mode
=========================================

Use ``Qlib`` in ``online`` mode according to the following steps:

- Open ``NFS`` Features in ``Qlib`` Client
- Initialize ``Qlib`` in ``online`` Mode

Opening ``NFS`` Features in ``Qlib`` Client
----------------------------------------

- If running on Linux, users need tp install ``nfs-common`` on the client, execute:
    .. code-block:: 
        
        sudo apt install nfs-common

- If running on Windows, do as follows.
    - Open ``Programs and Features``.
    - Click ``Turn Windows features on or off``.
    - Scroll down and check the option ``Services for NFS``, then click OK
    Reference address: https://graspingtech.com/mount-nfs-share-windows-10/

Initializing ``Qlib`` in ``online`` Mode
-----------------------------------------------

If users want to use ``Qlib`` in ``online`` mode, they can choose either of the following two methods to initialize ``Qlib``:

- Initialize ``Qlib`` with configuration file
- Initialize ``Qlib`` with arguments

Configuration File
-------------------
The content of configuration file is as follows.

.. code-block:: yaml

    calendar_provider: 
        class: LocalCalendarProvider
        kwargs: 
            remote: True
    feature_provider:
        class: LocalFeatureProvider
        kwargs: 
            remote: True
    expression_provider: LocalExpressionProvider
    instrument_provider: ClientInstrumentProvider
    dataset_provider: ClientDatasetProvider
    provider: ClientProvider
    expression_cache: null
    dataset_cache: null
    calendar_cache: null

    provider_uri: 127.0.0.1:/
    mount_path: /data/stock_data/qlib_data
    auto_mount: True
    flask_server: 127.0.0.1
    flask_port: 9710

- `provider_uri`
    nfs-server path; the format is ``host: data_dir``, for example: ``127.0.0.1:/``. If using ``Qlib`` in ``Local`` mode, it can be a local data directory.
- `mount_path`
    local data directory, ``provider_uri`` will be mounted to this directory
- `auto_mount`: 
    whether to automatically mount ``provider_uri`` to ``mount_path`` during qlib ``init``; 
    User can also mount it manually as follows.

    .. code-block:: 

        sudo mount.nfs <provider_uri> <mount_path>
    .. note::

        Automount requires sudo permission

- `flask_server`
    data service host/ip

- `flask_port`
    data service port


Initialize ``Qlib`` with parameters configuration file as follows.

.. code-block:: python

    import qlib
    qlib.init_from_yaml_conf("qlib_clinet_config.yaml")
    from qlib.data import D
    ins = D.list_instruments(D.instrumetns("all"), as_list=True)

.. note::

    If running ``Qlib`` on Windows, users should write correct **mount_path**.

    - In windows, mount path must be not exist path and root path,
        - correct format path eg: `H`, `i`...
        - error format path eg: `C`, `C:/user/name`, `qlib_data`...
    
    The configuration file can be:

    .. code-block:: YAML

        ...
        ...
        provider_uri: 127.0.0.1:/
        mount_path: H
        auto_mount: True
        flask_server: 127.0.0.1
        flask_port: 9710

    

Arguments
--------------------------

Initialize ``Qlib`` with arguments as follows.

.. code-block:: python

    import qlib

    # qlib client config

    ONLINE_CONFIG = {
        # data provider config
        "calendar_provider": {"class": "LocalCalendarProvider", "kwargs": {"remote": True}},
        "instrument_provider": "ClientInstrumentProvider",
        "feature_provider": {"class": "LocalFeatureProvider", "kwargs": {"remote": True}},
        "expression_provider": "LocalExpressionProvider",
        "dataset_provider": "ClientDatasetProvider",
        "provider": "ClientProvider",
        # config it in user's own code
        "provider_uri": "127.0.0.1:/",
        # cache
        # Using parameter 'remote' to announce the client is using server_cache, and the writing access will be disabled.
        "expression_cache": None,
        "dataset_cache": None,
        "calendar_cache": None,
        "mount_path": "/data/stock_data/qlib_data",
        "auto_mount": True,  # The nfs is already mounted on our server[auto_mount: False].
        "flask_server": "127.0.0.1",
        "flask_port": 9710,
        "region": "cn",
    }

    qlib.init(**client_config)
    ins = D.list_instruments(D.instrumetns("all"), as_list=True)

.. note::

    If running ``Qlib`` on Windows, users should write correct **mount_path**.

    The arguments can be:

    .. code-block:: python

        ONLINE_CONFIG = {
            ...
            ...
            "mount_path": "H",
            "auto_mount": True, 
            "flask_server": "127.0.0.1",
            "flask_port": 9710,
            "region": "cn",
        }
