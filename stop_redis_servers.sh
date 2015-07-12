#!/bin/bash

for i in 1 2 3 4 5 6 7 8 9; do kill `cat /tmp/redis$i.pid`; done;
