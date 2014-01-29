#!/bin/bash

python3.3 src/jobqueue.py --port 8315 --reset &
PID=$!
sleep 2
PYTHONPATH=src python3.3 -m unittest discover -p -s tests "*_test.py"
kill $PID
