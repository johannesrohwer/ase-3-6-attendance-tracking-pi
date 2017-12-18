#!/usr/bin/env python3

import requests
import zbar
from PIL import Image
import cv2

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
            cv2.imshow('Current', frame)

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
            for decoded in zbar_image:
                print(decoded.data)
                self.scannedString = decoded.data
                self.state_manager.set_state(Idle(self.state_manager))
                return



class StateManager:
    state = None

    def set_state(self, state):
        self.state = state
        self.state.execute()

    def handle_input(self, event):
        self.peek().handle_input(event)


if __name__ == "__main__":
    print('Welcome to ASE Attendance Tracking')
    sm = StateManager()
    #sm.set_state(Authentication(sm))
