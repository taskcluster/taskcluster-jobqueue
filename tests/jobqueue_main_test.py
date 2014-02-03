import amqp
import http.client
import json
import os
import psycopg2
import unittest
from urllib.parse import urlparse
import socket
import subprocess
import sys
import time

from jobqueue_testcase import JobQueueTestCase

# TODO: These tests are inherently kind of flaky due to spawning and
#       killing processes, using sleep to make sure things start up,
#       etc. I think these tests are worthwhile in the short term, 
#       but should be fixed up or turned off in the future.

# This code is taken from mozdevice (devicemanager.py)
def find_open_port(ip, seed):
    """Gets an open port starting with the seed by incrementing by 1 each time"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        connected = False
        if isinstance(seed, basestring):
            seed = int(seed)
        maxportnum = seed + 5000 # We will try at most 5000 ports to find an open one
        while not connected:
            try:
                s.bind((ip, seed))
                connected = True
                s.close()
                break
            except:
                if seed > maxportnum:
                    print('Error: Could not find open port after checking {} ports'.format(maxportnum))
                    raise
            seed += 1
    except:
        print('Error: Socket error trying to find open port')

    return seed


class TestJobQueueMain(JobQueueTestCase):

    @classmethod
    def setUpClass(cls):
        cls.python = 'python{}.{}'.format(sys.version_info.major, sys.version_info.minor)
        cls.jobqueue_path = None
        paths = ['src/jobqueue.py', '../src/jobqueue.py']
        for path in paths:
            if os.path.isfile(path):
                cls.jobqueue_path = path
                break

    def check_port(self, port):
        conn = http.client.HTTPConnection('localhost', port)
        conn.request('GET', '/0.1.0/jobs')
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)

    def check_stderr(self, proc):

        err = proc.stderr.read()
        proc.stderr.close()
        if len(err):
            print(err)
        self.assertEqual(len(err), 0)
        self.assertNotEqual(proc.returncode, 1)

    def test_defaults(self):
        self.assertIsNotNone(TestJobQueueMain.jobqueue_path)
        cmd = [TestJobQueueMain.python, TestJobQueueMain.jobqueue_path]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)
        time.sleep(2)

        # check default port
        self.check_port(8314)

        proc.terminate()
        proc.wait()
        self.check_stderr(proc)

    def test_port(self):
        self.assertIsNotNone(TestJobQueueMain.jobqueue_path)

        port = find_open_port('127.0.0.1', 15555)
        self.assertGreaterEqual(port, 15555)

        cmd = [TestJobQueueMain.python, TestJobQueueMain.jobqueue_path, '--port', str(port)]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)
        time.sleep(2)

        # see if we can connect to the specified port
        self.check_port(port)

        proc.terminate()
        proc.wait()
        self.check_stderr(proc)

    def test_reset(self):
        self.assertIsNotNone(TestJobQueueMain.jobqueue_path)
        cmd = [TestJobQueueMain.python, TestJobQueueMain.jobqueue_path, '--reset']
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)
        time.sleep(2)

        # check database
        dsn = 'dbname=jobqueue user=jobqueue host=localhost password=jobqueue'
        dbconn = psycopg2.connect(dsn)
        cursor = dbconn.cursor()
        cursor.execute('select job_id from Job')
        self.assertEqual(cursor.rowcount, 0)
        dbconn.close()

        #TODO: find nice way to verify rabbitmq has been purged

        proc.terminate()
        proc.wait()
        self.check_stderr(proc)

    def test_external_addr(self):
        self.assertIsNotNone(TestJobQueueMain.jobqueue_path)

        jobqueue_external_addr = '42.42.42.42'

        cmd = [TestJobQueueMain.python, TestJobQueueMain.jobqueue_path, '--external-addr', jobqueue_external_addr]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)
        time.sleep(2)

        # new job
        job = {'version': '0.1.0'}
        conn = http.client.HTTPConnection('localhost', 8314)
        headers = {"Content-Type": "application/json",
                   "Content-Length": len(json.dumps(job))}
        conn.request("POST", "/0.1.0/job/new", json.dumps(job), headers)
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        res = self.get_json(resp)
        conn.close()

        # get a job from the queue
        rabbit_conn = amqp.Connection(host='localhost:5672', userid="guest", password="guest", virtual_host="/", insist=False)
        rabbit_chan = rabbit_conn.channel()

        res = self.wait_for_job(rabbit_chan)
        self.assertIsNot(res, None)
        our_job = json.loads(res)

        # check urls
        parsed = urlparse(our_job['claim'])
        self.assertTrue(jobqueue_external_addr == parsed.netloc)

        parsed = urlparse(our_job['finish'])
        self.assertTrue(jobqueue_external_addr == parsed.netloc)

        proc.terminate()
        proc.wait()
        self.check_stderr(proc)

if __name__ == '__main__':
    unittest.main()
