#!/bin/bash

# run unit tests
python3.3 src/jobqueue.py --port 8315 --reset &
PID=$!
sleep 2
PYTHONPATH=src python3.3 -m unittest discover -p -s tests "*_test.py"
kill $PID

# run stresstest 
python3.3 src/jobqueue.py --reset &
PID=$!
sleep 2
./stresstest/stresstest.py
if [ $? -eq 0 ]
then echo 'OK'
fi
kill $PID
