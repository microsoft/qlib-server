Changelog
====================
Here you can see the full list of changes between each QLibServer release.

Version 0.1.0
--------------------
This is the initial release of QLibServer.


Version 0.1.1
--------------------
- Fix multi-process log bug, using ``logging.handlers.QueueHandler``
- Modify to create a rabbitmq ``connection`` and ``channel`` for each process, before sharing a one that causes ``basic_ack`` to be unsuccessful
- Add ``max_process`` to config
- The log is set through the configuration file, refer to config.yaml.example


Version 0.1.2
--------------------
- Format PEP8
