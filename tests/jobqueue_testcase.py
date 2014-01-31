import json
import psycopg2
import unittest

class JobQueueTestCase(unittest.TestCase):

    def clear_database(self, dsn):
        dbconn = psycopg2.connect(dsn)
        cursor = dbconn.cursor()
        cursor.execute('delete from Job');
        cursor.execute('delete from Worker');
        dbconn.commit()

    def get_json(self, response, expected_status=200):
        self.assertEqual(response.status, expected_status)

        try:
            text = response.read().decode().strip()
            decoded = json.loads(text)
        except:
            self.fail('could not parse json')

        return decoded

    def wait_for_job(self, rabbit_chan):
        count = 0
        msg = rabbit_chan.basic_get(queue='jobs')
        while not msg:
            os.sleep(1)
            msg = rabbit_chan.basic_get(queue='jobs')
            count = count + 1
            if count > 5:
                break

        self.assertIsNotNone(msg)
        self.assertIsNotNone(msg.body)

        return msg.body
