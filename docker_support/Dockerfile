FROM continuumio/miniconda3:4.8.2

ARG DEFAULT_HOST=127.0.0.1
ARG QLIB_DATA=/data/stock_data/qlib_data
ARG QUEUE_HOST=$DEFAULT_HOST
ARG REDIS_HOST=$DEFAULT_HOST
ARG QUEUE_USER=guest
ARG QUEUE_PASS=guest
ARG FLASK_SERVER_HOST=$DEFAULT_HOST
ARG QLIB_CODE=/code
ARG SERVER_DIR=$QLIB_CODE/qlib-server

WORKDIR $SERVER_DIR
COPY . .

RUN apt-get update\
    && apt-get install -y g++\
    && apt-get clean\
    && rm -rf /var/lib/apt/lists/*\
    && cd ..\
    && git clone https://github.com/Microsoft/qlib\
    && cd qlib\
    && pip install --upgrade pip\
    && pip install --upgrade cython packaging numpy\
    && python setup.py install\
    && cd $SERVER_DIR\
    && python setup.py install\
    && /bin/sed -i "s@<QLIB_DATA>@$QLIB_DATA@g" config_template.yaml\
    && /bin/sed -i "s@<QUEUE_HOST>@$QUEUE_HOST@g" config_template.yaml\
    && /bin/sed -i "s@<REDIS_HOST>@$REDIS_HOST@g" config_template.yaml\
    && /bin/sed -i "s@<QUEUE_USER>@$QUEUE_USER@g" config_template.yaml\
    && /bin/sed -i "s@<QUEUE_PASS>@$QUEUE_PASS@g" config_template.yaml\
    && /bin/sed -i "s@<FLASK_SERVER_HOST>@$FLASK_SERVER_HOST@g" config_template.yaml\
    && git clone https://github.com/vishnubob/wait-for-it.git

EXPOSE 9710
CMD ["python", "main.py", "-c", "config_template.yaml"]
