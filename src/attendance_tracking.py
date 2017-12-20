#!/usr/bin/env python3

import requests
import zbar
from PIL import Image
import cv2
import jwt
import pifacecad

import os
import signal
import sys

# you can ignore these three lines of code
# they are needed so that you can end the
# program by pressing Ctrl+C
def signal_handler(signal, frame):
    if sys.version_info < (3,0):
        # the python2 code forks
        os.kill(os.getppid(),9)
    os.kill(os.getpid(),9)
signal.signal(signal.SIGINT, signal_handler)


class Constants(object):
    BASE_URL = 'https://ase-3-6-attendance-tracking.appspot.com'
    AUTH_TOKEN = ""


class State(object):
    state_manager = None
    data = None

    def __init__(self, state_manager, data=None):
        self.state_manager = state_manager
        self.data = data

    def execute(self):
        print("- - -")

    def handle_input(self, event):
        raise NotImplementedError

    def transition(self):
        raise NotImplementedError


class Idle(State):
    def execute(self):
        print("Idle state")
        self.state_manager.set_state(Scan(self.state_manager))


class Authentication(State):
    id = None
    password = None
    authorization_token = None

    def execute(self):
        super(Authentication, self).execute()

        print("Authentication State")
        # Get credentials from user
        print('Please authenticate yourself.')
        self.id = raw_input('ID:\t')
        self.password = raw_input('password:\t')

        # Send credentials to API and obtain Authorization token
        url = Constants.BASE_URL + '/api/login'
        payload = {'id': self.id,
                   'password': self.password}
        response = requests.post(url, json=payload)
        responseObj = response.json()

        if response.status_code == 200:
            self.authorization_token = responseObj["token"]
            print(self.authorization_token) # TODO: Remove

        else:
            print("An error occured: {}".format(responseObj["error"]))

        self.transition()

    def handle_input(self, event):
        return

    def transition(self):
        if self.authorization_token:
            Constants.AUTH_TOKEN = self.authorization_token

            # Perform the transition to the next state
            self.state_manager.set_state(Idle(self.state_manager))

        else:
            # An error occured, start again
            self.state_manager.set_state(Authentication(self.state_manager))


class Scan(State):
    def execute(self):
        print("Scan State")
        self.scanQRCode()

    def handle_input(self, event):
        pass

    def transition(self):
        raise NotImplementedError

    def scanQRCode(self):
        capture = cv2.VideoCapture(0)

        # Search until you find a QR Code to decode
        while True:
            # Breaks down the video into frames
            ret, frame = capture.read()

            # Displays the current frame
            # cv2.imshow('Current', frame)

            # Converts image to grayscale.
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Uses PIL to convert the grayscale image into a ndary array that ZBar can understand.
            image = Image.fromarray(gray)
            width, height = image.size
            zbar_image = zbar.Image(width, height, 'Y800', image.tobytes())

            # Scans the zbar image.
            scanner = zbar.ImageScanner()
            scanner.scan(zbar_image)

            # Prints data from image.
            qr_payload = None

            for decoded in zbar_image:
                print(decoded.data)
                qr_payload = decoded.data
                self.state_manager.set_state(Verify(self.state_manager, data=qr_payload))
                return

                # TODO: re-add this line when we have proper interrupt handling...
                # self.state_manager.set_state(Idle(self.state_manager, data=qr_payload))


class Verify(State):
    def execute(self):
        print("Entering verify")
        token = self.data
        decoded_token = jwt.decode(token, verify=False)  # TODO: enable signature validation
        print(decoded_token)
        cad.lcd.write("Student:"+decoded_token["attendance"]["student_id"])
        if decoded_token["attendance"]["presented"]:
            self.state_manager.set_state(Presented(self.state_manager, data={'token': token}))
        else:
            self.state_manager.set_state(Send(self.state_manager, data={'token': token}))

class Presented(State):
    ok = None
    choice_made = False

    def execute(self):
        cad.lcd.clear()
        cad.lcd.write('presented?')

        while not self.choice_made:
            pass

        if self.ok:
            self.state_manager.set_state(Send(self.state_manager, data=self.data))
        else:
            self.state_manager.set_state(Idle(self.state_manager))

    def handle_input(self, event):
        if event.pin_num == 0:
            self.choice_made = True
            self.ok = True
        elif event.pin_num == 1:
            self.choice_made = True
            self.ok = False

    def transition(self):
        # TODO: check if presentation status was approved
        pass


class Send(State):
    def execute(self):
        print("- - -")

        # Send the data to the server and mark the attendance
        url = Constants.BASE_URL + '/api/attendances/register'

        payload = self.data

        print(payload)
        response = requests.post(url, headers={'Authorization': Constants.AUTH_TOKEN}, json=payload)
        response_obj = response.json()
        print(response.url)

        print("rsponse code")
        print(response.status_code)
        if response.status_code == 201 or response.status_code == 200:
            print("The attendance has been tracked.")

            cad.lcd.clear()
            cad.lcd.write('Tracked!')

        else:
            print("An error occured: {}".format(response_obj["error"]))

        self.transition()

    def handle_input(self, event):
        raise NotImplementedError

    def transition(self):
        # self.state_manager.set_state(Idle(self.state_manager))
        while True:
                pass

class StateManager:
    state = None

    def set_state(self, state):
        self.state = state
        self.state.execute()

    def handle_input(self, event):
        self.state.handle_input(event)


if __name__ == "__main__":
    print('Welcome to ASE Attendance Tracking')
    sm = StateManager()

    # get an object for the display
    cad = pifacecad.PiFaceCAD()

    # write a string to the display
    # cad.lcd.write("Hello, world!")

    # read the value of a switch
    # cad.switches[3].value

    # create a listener:
    listener = pifacecad.SwitchEventListener(chip=cad)

    # bind all switches to handler
    for i in range(8):
        listener.register(i, pifacecad.IODIR_FALLING_EDGE, sm.handle_input)

    listener.activate()

    sm.set_state(Authentication(sm))
