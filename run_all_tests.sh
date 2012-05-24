#!/bin/bash

./run_tests.py --settings=tests.settings
./run_tests.py --settings=tests.python_parser_settings
./run_tests.py --settings=tests.sockets_settings