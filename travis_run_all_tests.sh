#!/bin/bash

./run_tests.py --settings=tests.hiredis_parser_settings -s ../redis/src/redis-server --redis-version=$REDIS_VERSION
./run_tests.py --settings=tests.python_parser_settings -s ../redis/src/redis-server --redis-version=$REDIS_VERSION
./run_tests.py --settings=tests.sockets_settings -s ../redis/src/redis-server --redis-version=$REDIS_VERSION