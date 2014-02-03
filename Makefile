DATABASE_USER?=postgres

default:

# need to run as sudo -u postgres
database:
	cd sql; sudo -u $(DATABASE_USER) ./createdb.sh

run:
	python3.3 src/jobqueue.py

test:
	./run-tests.sh

