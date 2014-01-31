
default:

# need to run as sudo -u postgres
database:
	cd sql; sudo -u postgres ./createdb.sh

run:
	python3.3 src/jobqueue.py

test:
	./run-tests.sh

