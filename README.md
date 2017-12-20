# ase-3-6-attendance-tracking-pi

This repository contains the Raspberry Pi project for the ASE Attendance Tracking System of the group 3-6

## Setup Instructions
Please make sure to run the following commands before getting started (this assumes you have a "clean" Raspberry Pi, as handed out by the chair).

``` 
sudo apt-get -y install python-pip
sudo apt-get install libzbar-dev
sudo apt-get install python-opencv
sudo pip install pillow
sudo pip install requests
sudo pip install pyjwt
sudo pip install git+https://github.com/npinchot/zbar.git
```

## Troubleshooting

- __The camera cannot read the QR Code, no matter how I hold it.__

In case you have a glossy screen, try covering the lights of the camera. This has solved all issues for us while testing on a MacBook Pro. Also, make sure to properly focus ;)

- __Is this compatible with Python 3?__

No. ¯\_(ツ)_/¯

## Server & Web Frontend Repository

The repository containing the server implementation and web frontend can be found here:
https://github.com/johannesrohwer/ase-3-6-attendance-tracking-web

## Android App Repository

The repository containing the Android application can be found here:

https://github.com/PSchmiedmayer/ase-3-6-attendance-tracking-android
