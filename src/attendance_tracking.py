import requests
import zbar
from PIL import Image
import cv2
import jwt
import pifacecad
import os
import signal
import sys


# Enable Ctrl+C quit of program
def signal_handler(signal, frame):
    if sys.version_info < (3, 0):
        # the python2 code forks
        os.kill(os.getppid(), 9)
    os.kill(os.getpid(), 9)


signal.signal(signal.SIGINT, signal_handler)


# Base URL and authentication token for API communication
class Constants(object):
    BASE_URL = 'https://ase-3-6-attendance-tracking.appspot.com'
    AUTH_TOKEN = ""


# Base Class of a State, handled by a StateManager.
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


# Subclasses of the State Class.

# Authentication State, checks the credentials of the instructor/tutor.
class Authentication(State):
    id = None
    password = None
    authorization_token = None

    def execute(self):
        print("Authentication State")

        # Get credentials from user.
        print('Please authenticate yourself.')
        self.id = raw_input('ID:\t')
        self.password = raw_input('password:\t')

        # Send credentials to API and obtain Authorization token.
        url = Constants.BASE_URL + '/api/login'
        payload = {'id': self.id,
                   'password': self.password}
        response = requests.post(url, json=payload)
        response_obj = response.json()

        if response.status_code == 200:
            self.authorization_token = response_obj["token"]
            # print(self.authorization_token)

        else:
            print("An error occured: {}".format(response_obj["error"]))

        self.transition()

    def handle_input(self, event):
        return

    # If the authorization token was correct, change State to Idle, otherwise,
    # try authenticating once again.
    def transition(self):
        if self.authorization_token:
            Constants.AUTH_TOKEN = self.authorization_token

            # Perform the transition to the next state
            self.state_manager.set_state(Idle(self.state_manager))

        else:
            # An error occured, start again
            self.state_manager.set_state(Authentication(self.state_manager))


# Idle State of the program. As of now, will change into the Scan State immediately.
class Idle(State):
    def execute(self):
        print("Idle state")

        # TODO: Consider if we want to have another branch from the Idle State
        # to another one.
        self.state_manager.set_state(Scan(self.state_manager))


# Scan State, waits for the QR Code to be scanned and processes it.
class Scan(State):
    qr_payload = None

    def execute(self):
        print("Scan State")
        self.scanQRCode()

    # No input handling needed for this State, tutor just has to hold camera
    # in front of QR Code.
    def handle_input(self, event):
        pass

    def scanQRCode(self):
        capture = cv2.VideoCapture(0)

        # Search until you find a QR Code to decode.
        while True:
            # Breaks down the video into frames.
            ret, frame = capture.read()

            # Converts image to grayscale.
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Uses PIL to convert the grayscale image into a ndary array that ZBar can understand.
            image = Image.fromarray(gray)
            width, height = image.size
            zbar_image = zbar.Image(width, height, 'Y800', image.tobytes())

            # Scans the zbar image.
            scanner = zbar.ImageScanner()
            scanner.scan(zbar_image)

            for decoded in zbar_image:
                # print(decoded.data)
                self.qr_payload = decoded.data
                self.transition()
                return

                # TODO: re-add this line when we have proper interrupt handling...
                # self.state_manager.set_state(Idle(self.state_manager, data=qr_payload))

    def transition(self):
        self.state_manager.set_state(Verify(self.state_manager, data=self.qr_payload))


# Checks whether the student wants to track attendance for the correct group, and if they selected
# in the Android app whether they presented or not.
class Verify(State):
    presented = None

    def execute(self):
        print("Verify State")

        token = self.data
        decoded_token = jwt.decode(token, verify=False)  # TODO: enable signature validation

        # print(decoded_token)
        cad.lcd.write("Student:" + decoded_token["attendance"]["student_id"])
        self.presented = decoded_token["attendance"]["presented"]

        self.transition()

    # Depending on whether the student presented or not, transition to Send or Presented State.
    def transition(self):
        token = self.data
        if self.presented:
            self.state_manager.set_state(Presented(self.state_manager, data={'token': token}))
        else:
            self.state_manager.set_state(Send(self.state_manager, data={'token': token}))


# In the Presented State the tutor can confirm whether the user really presented or not.
class Presented(State):
    ok = None
    choice_made = False

    def execute(self):
        print("Presented State")

        # Write out prompt to piface.
        cad.lcd.clear()
        cad.lcd.write('Presented?')

        while not self.choice_made:
            pass

        # As soon tutor made a choice, move to the appropriate next state.
        self.transition()

    def handle_input(self, event):
        if event.pin_num == 0:
            self.choice_made = True
            self.ok = True
        elif event.pin_num == 1:
            self.choice_made = True
            self.ok = False

    def transition(self):
        if self.ok:
            self.state_manager.set_state(Send(self.state_manager, data=self.data))
        else:
            self.state_manager.set_state(Idle(self.state_manager))


# In the Send State the attendance is being sent to the server and tracked.
class Send(State):
    def execute(self):
        print("Send State")

        # Send the data to the server and mark the attendance
        url = Constants.BASE_URL + '/api/attendances/register'
        payload = self.data
        response = requests.post(url, headers={'Authorization': Constants.AUTH_TOKEN}, json=payload)
        response_obj = response.json()

        # Display message to piface in case of success.
        if response.status_code == 201 or response.status_code == 200:
            # print("The attendance has been tracked.")

            cad.lcd.clear()
            cad.lcd.write('Tracked!')

        else:
            print("An error occured: {}".format(response_obj["error"]))

        self.transition()

    def handle_input(self, event):
        raise NotImplementedError

    def transition(self):
        # self.state_manager.set_state(Idle(self.state_manager))
        # TODO: For now, the program does not have a loop back into the idle state.
        while True:
            pass


# StateManager handles all States internally and propagates input events to the appropriate subclass of the state.
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

    # Get an object for the display.
    cad = pifacecad.PiFaceCAD()

    # Create a listener.
    listener = pifacecad.SwitchEventListener(chip=cad)

    # Bind all switches to handler.
    for i in range(8):
        listener.register(i, pifacecad.IODIR_FALLING_EDGE, sm.handle_input)

    listener.activate()

    # Start the State Machine.
    sm.set_state(Authentication(sm))
