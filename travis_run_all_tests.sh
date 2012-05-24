#!/bin/bash

./run_tests.py --settings=tests.settings -s ../redis/src/redis-server
./run_tests.py --settings=tests.python_parser_settings -s ../redis/src/redis-server
./run_tests.py --settings=tests.sockets_settings -s ../redis/src/redis-server