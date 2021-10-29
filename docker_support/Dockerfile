FROM continuumio/miniconda3:4.8.2

ARG DEFAULT_HOST=127.0.0.1
ARG QLIB_DATA=/data/stock_data/qlib_data
ARG QUEUE_HOST=$DEFAULT_HOST
ARG QUEUE_USER=guest
ARG QUEUE_PASS=guest
ARG MESSAGE_QUEUE=$MESSAGE_QUEUE
ARG TASK_QUEUE=$TASK_QUEUE
ARG REDIS_HOST=$DEFAULT_HOST
ARG REDIS_PORT=6379
ARG REDIS_DB=$REDIS_DB
ARG FLASK_SERVER_HOST=$DEFAULT_HOST
ARG QLIB_CODE=/code
ARG SERVER_DIR=$QLIB_CODE/qlib-server

WORKDIR $SERVER_DIR
COPY . .

RUN apt-get --allow-releaseinfo-change update\
    && apt-get install -y g++\
    && apt-get clean\
    && rm -rf /var/lib/apt/lists/*\
    && pip install cython numpy -U\
    && pip install git+https://github.com/microsoft/qlib\
    && cd $SERVER_DIR\
    && python setup.py install\
    && pip install -U python-engineio==3.11.2 python-socketio==4.4.0 flask-socketio==3.1.2\
    && /bin/sed -i "s@<QLIB_DATA>@$QLIB_DATA@g" config_template.yaml\
    && /bin/sed -i "s@<QUEUE_HOST>@$QUEUE_HOST@g" config_template.yaml\
    && /bin/sed -i "s@<QUEUE_USER>@$QUEUE_USER@g" config_template.yaml\
    && /bin/sed -i "s@<QUEUE_PASS>@$QUEUE_PASS@g" config_template.yaml\
    && /bin/sed -i "s@<TASK_QUEUE>@$TASK_QUEUE@g" config_template.yaml\
    && /bin/sed -i "s@<MESSAGE_QUEUE>@$MESSAGE_QUEUE@g" config_template.yaml\
    && /bin/sed -i "s@<REDIS_HOST>@$REDIS_HOST@g" config_template.yaml\
    && /bin/sed -i "s@<REDIS_PORT>@$REDIS_PORT@g" config_template.yaml\
    && /bin/sed -i "s@<REDIS_DB>@$REDIS_DB@g" config_template.yaml\
    && /bin/sed -i "s@<FLASK_SERVER_HOST>@$FLASK_SERVER_HOST@g" config_template.yaml\
    && git clone https://github.com/vishnubob/wait-for-it.git

EXPOSE 9710
CMD ["python", "main.py", "-c", "config_template.yaml"]
