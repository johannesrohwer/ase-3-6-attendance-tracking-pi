import zbar
from PIL import Image
import cv2
from attendance_tracking import State

class Scan(State):
    state_manager = None

    def __init__(self, state_manager):
        self.state_manager = state_manager

    def execute(self):
        print("Scan State")
        self.scanQRCode()

    def handle_input(self, event):
        raise NotImplementedError

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
                return

