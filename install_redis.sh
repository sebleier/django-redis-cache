#!/bin/bash

: ${REDIS_VERSION:="7.0.0"}

test -d redis || git clone https://github.com/antirez/redis
git -C redis checkout $REDIS_VERSION
make -C redis
