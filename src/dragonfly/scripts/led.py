#! /usr/bin/env python
import argparse
import time
import RPi.GPIO as GPIO

# LED pin mapping.
red = 18
green = 17
blue = 4

# GPIO setup.
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(red, GPIO.OUT)
GPIO.setup(green, GPIO.OUT)
GPIO.setup(blue, GPIO.OUT)

# Set up colors using PWM so we can control individual brightness.
RED = GPIO.PWM(red, 100)
GREEN = GPIO.PWM(green, 100)
BLUE = GPIO.PWM(blue, 100)
RED.start(100)
GREEN.start(100)
BLUE.start(100)

# Set a color by giving R, G, and B values of 0-255.
def setColor(rgb = []):
    # Convert 0-255 range to 0-100.
    rgb = [(x / 255.0) * 100 for x in rgb]
    RED.ChangeDutyCycle(100 - rgb[0])
    GREEN.ChangeDutyCycle(100 - rgb[1])
    BLUE.ChangeDutyCycle(100 - rgb[2])



if __name__ == '__main__':
    # Get RGB colors from command line arguments.
    parser = argparse.ArgumentParser(description = 'Light up the world!')
    parser.add_argument('rgb', metavar='0-255', type=int, nargs=3, help='Red, Green, and Blue color values (0-255).')
    args = parser.parse_args()
    setColor(args.rgb)
    time.sleep(60)

    GPIO.cleanup()
