#!/bin/bash

: ${REDIS_VERSION:="2.6"}

test -d redis || git clone https://github.com/antirez/redis
git -C redis checkout $REDIS_VERSION
make -C redis

for i in 1 2 3; do \
    ./redis/src/redis-server \
        --pidfile /tmp/redis`echo $i`.pid \
        --requirepass yadayada \
        --daemonize yes \
        --port `echo 638$i` ; \
    done

for i in 4 5 6; do \
    ./redis/src/redis-server \
        --pidfile /tmp/redis`echo $i`.pid \
        --requirepass yadayada \
        --daemonize yes \
        --port 0 \
        --unixsocket /tmp/redis`echo $i`.sock \
        --unixsocketperm 755 ; \
    done

    ./redis/src/redis-server \
        --pidfile /tmp/redis7.pid \
        --requirepass yadayada \
        --daemonize yes \
        --port 6387 ;

for i in 8 9; do \
    ./redis/src/redis-server \
        --pidfile /tmp/redis`echo $i`.pid \
        --requirepass yadayada \
        --daemonize yes \
        --masterauth yadayada \
        --slaveof 127.0.0.1 6387 \
        --port `echo 638$i` ; \
    done
