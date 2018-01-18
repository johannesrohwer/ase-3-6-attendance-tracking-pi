import requests
import zbar
from PIL import Image
import cv2
import jwt
import pifacecad
import os
import signal
import sys
import time
import getpass


LEFT_BUTTON = 0
RIGHT_BUTTON = 4


# Enable Ctrl+C quit of program
def signal_handler(signal, frame):
    cad.lcd.clear()

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

    def write_state_to_piface(self, state, left="", right=""):
        cad.lcd.clear()
        cad.lcd.write(state)
        write_ui(left, right)


# Subclasses of the State Class.

# Authentication State, checks the credentials of the instructor/tutor.
class Authentication(State):
    id = None
    password = None
    authorization_token = None

    def execute(self):
        print("Authentication State")

        # Write current state to piface.
        super(Authentication, self).write_state_to_piface("Authentication")

        # Get credentials from user.
        params = sys.argv
        if len(params) > 2:
            self.id = params[1]
            self.password = params[2]
        else:
            print('Please authenticate yourself.')
            self.id = raw_input("ID:\t")
            self.password = getpass.getpass("password: \t")


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
    start = False
    cancel = False

    def execute(self):
        print("Idle state")

        # Write current state to piface.
        super(Idle, self).write_state_to_piface("Idle", left="SCAN", right="END")

        while not self.start:
            pass

        self.transition()

    # Perform transition to Scan State when button is pushed.
    def handle_input(self, event):
        if event.pin_num == LEFT_BUTTON:
            self.start = True
        if event.pin_num == RIGHT_BUTTON:
            cad.lcd.clear()
            os.kill(os.getpid(), 9)

    def transition(self):
        self.state_manager.set_state(Scan(self.state_manager))



# Scan State, waits for the QR Code to be scanned and processes it.
class Scan(State):
    qr_payload = None
    cancel = False

    def execute(self):
        print("Scan State")

        # Write current state to piface.
        super(Scan, self).write_state_to_piface("Scan", right="CANCEL")

        self.scanQRCode()

    # Handle cancelling of Scan State from user side, return back to Idle.
    def handle_input(self, event):
        if event.pin_num == RIGHT_BUTTON:
            self.cancel = True

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
                capture.release()
                self.transition()

                return

            if self.cancel:
                capture.release()
                self.transition()


    def transition(self):
        if self.cancel:
            self.state_manager.set_state(Idle(self.state_manager))
        else:
            self.state_manager.set_state(Verify(self.state_manager, data=self.qr_payload))


# Checks whether the student wants to track attendance for the correct group, and if they selected
# in the Android app whether they presented or not.
class Verify(State):
    presented = None
    cancel = False

    def execute(self):
        print("Verify State")

        # Write current state to piface.
        super(Verify, self).write_state_to_piface("Verify")

        token = self.data
        decoded_token = jwt.decode(token, verify=False)  # TODO: enable signature validation

        # print(decoded_token)
        cad.lcd.clear()
        cad.lcd.write("Student:" + decoded_token["attendance"]["student_id"])

        self.presented = decoded_token["attendance"]["presented"]

        self.transition()

    # Handle cancelling of Verify State from user side, return back to Idle.
    def handle_input(self, event):
        if event.pin_num == 3:
            self.cancel = True

    # Depending on whether the student presented or not, transition to Send or Presented State.
    def transition(self):

        token = self.data

        if self.cancel:
            self.state_manager.set_state(Idle(self.state_manager))

        elif self.presented:
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
        # cad.lcd.clear()
        # cad.lcd.write('Presented?')

        # Write current state to piface.
        super(Presented, self).write_state_to_piface("Presented?", left="YES", right="NO")

        while not self.choice_made:
            pass

        # As soon tutor made a choice, move to the appropriate next state.
        self.transition()


    def handle_input(self, event):

        # Handle the yes/no prompt.
        if event.pin_num == LEFT_BUTTON:
            self.choice_made = True
            self.ok = True

        elif event.pin_num == RIGHT_BUTTON:
            self.choice_made = True
            self.ok = False

    def transition(self):
        if self.ok:
            self.state_manager.set_state(Send(self.state_manager, data=self.data))

        else:
            self.state_manager.set_state(Idle(self.state_manager))


# In the Send State the attendance is being sent to the server and tracked.
class Send(State):

    finish = False

    def execute(self):
        print("Send State")

        # Write current state to piface.
        super(Send, self).write_state_to_piface("Sending...")

        # Send the data to the server and mark the attendance
        url = Constants.BASE_URL + '/api/attendances/register'
        payload = self.data
        response = requests.post(url, headers={'Authorization': Constants.AUTH_TOKEN}, json=payload)
        response_obj = response.json()

        time.sleep(1)

        # Display message to piface in case of success.
        if response.status_code == 201 or response.status_code == 200:
            # print("The attendance has been tracked.")

            cad.lcd.clear()
            cad.lcd.write('Tracked!')
            write_ui(left="OK")

        else:
            print("An error occured: {}".format(response_obj["error"]))

        while not self.finish:
            pass

        self.transition()

    def handle_input(self, event):
        if event.pin_num == LEFT_BUTTON:
            self.finish = True

    def transition(self):

        if self.finish:
            self.state_manager.set_state(Idle(self.state_manager))

        if self.cancel:
            self.state_manager.set_state(Idle(self.state_manager))






def write_ui(left="", right=""):

   if left is not "":
       cad.lcd.set_cursor(0, 1)
       cad.lcd.write(left)

   if right is not "":
       cad.lcd.set_cursor(8, 1)
       cad.lcd.write(right)



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
    cad.lcd.cursor_off()

    # Create a listener.
    listener = pifacecad.SwitchEventListener(chip=cad)

    # Bind all switches to handler.
    for i in range(8):
        listener.register(i, pifacecad.IODIR_FALLING_EDGE, sm.handle_input)

    listener.activate()

    # Start the State Machine.
    sm.set_state(Authentication(sm))
