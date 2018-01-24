import json
import os
import threading
import time

import jwt
import requests
from google.cloud import pubsub_v1  # add this via: pip install --upgrade google-cloud-pubsub
import uuid
import Queue

# Environment variables and constants
HOST_ID = str(uuid.uuid4())
GOOGLE_CLOUD_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]


class Message():
    """
    This class provides the required message format for the pubsub communication.
    """

    def __init__(self, instruction_type, message_type, to, payload):
        self.payload = payload
        self.to = to
        self.message_type = message_type
        self.instruction_type = instruction_type
        self.From = HOST_ID # unique identifier; has to be capitalized since the lowercase from is a python keyword -.-

    def toJSONString(self):
        d = vars(self)

        # Rename from key since lowercase from is a reserved python keyword
        d["from"] = d.pop("From")
        payload_json = json.dumps(d)

        return payload_json


def process_attendance(attendance_token):
    """ Sends an attendance token to the backend datastore and adds it to the blockchain. """
    add_attendance_to_chain(attendance_token)
    add_attendance_to_server(attendance_token)


def add_attendance_to_chain(attendance_token):
    """ Adds an attendance to the blockchain. """

    decoded_token = jwt.decode(attendance_token, verify=False)
    attendance_pubsub = json.dumps(decoded_token["attendance"])
    msg = Message("add_broadcast", "broadcast", "", {"content": attendance_pubsub})
    publish("add", msg)


def add_attendance_to_server(attendance_token):
    """ Adds an attendance to the datastore on the server"""
    url = Constants.BASE_URL + '/api/attendances/register'
    payload = {"token": attendance_token}
    response = requests.post(url, headers={'Authorization': Constants.AUTH_TOKEN}, json=payload)
    response_obj = response.json()

    if response.status_code == 201 or response.status_code == 200:
        print("The attendance has been tracked.")
    else:
        print("An error occured: {}".format(response_obj["error"]))


def publish(topic_name, msg):
    """ Publishes a Message object to the given topic. """
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(GOOGLE_CLOUD_PROJECT, topic_name)
    payload_json = msg.toJSONString()
    publisher.publish(topic_path, data=payload_json)
    print("Published: {}".format(payload_json))


# Queueing mechanism and offline mode.
task_queue = Queue.Queue()

def add_attendance(attendance_JSON_string):
    """ Schedules the adding of an attendance object. """
    task_queue.put_nowait(attendance_JSON_string)


def isOnline():
    """ Checks if https://ase-3-6-attendance-tracking.appspot.com/api/version is reachable within 2 sec. """
    try:
        requests.get("https://ase-3-6-attendance-tracking.appspot.com/api/version", timeout=2.0)
    except Exception:
        return False

    return True


class QueueWorker(threading.Thread):
    """ A thread that processes the task_queue elements. """
    done = False

    def join(self, timeout=None):
        self.done = True

    def run(self):

        while not self.done:
            if isOnline():
                # FIXME: The queue.get() method provides a timeout parameter that might be handy
                # The normal .get() blocks if the queue is empty which might skip the isOnline() test.
                attendance_token = task_queue.get()
                process_attendance(attendance_token)
            else:
                print("OFFLINE") # TODO: remove unnecessary debug print

        time.sleep(10)


qw = QueueWorker()
qw.start()
add_attendance(
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdHRlbmRhbmNlIjp7ImlkIjoiMDdiZjVlYjAtNjQyNS00YTM5LTkyMjMtZDY4ZTA5ZGM3NGU5Iiwid2Vla19pZCI6IjgiLCJwcmVzZW50ZWQiOnRydWUsInN0dWRlbnRfaWQiOiI4ODg4MDAwMCIsImdyb3VwX2lkIjoiMDEifSwiZXhwIjoiMjAxOC0wMS0yNVQxMzoyMDozOC4xMjk3Mzg4ODRaIn0.49BKdvZfdaBQt0_C4tg1Nl3b6nVmhdAR9HNrhnnxjSI")

while True:
    # let the main thread continue
    time.sleep(5)
