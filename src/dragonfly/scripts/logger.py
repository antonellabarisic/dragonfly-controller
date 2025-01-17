#!/usr/bin/env python
import argparse
import sched
import time
from datetime import datetime, timedelta

import rospy
from sensor_msgs.msg import NavSatFix, TimeReference
from dragonfly_messages.msg import CO2
from std_msgs.msg import String

from led import LED

class co2Logger:

    def __init__(self, id):
        self.id = id

        self.position = None
        self.positionReceived = None
        self.co2Received = None
        self.led = LED()
        self.sincezero = datetime.now()
        self.zeroing = False
        self.s = sched.scheduler(time.time, time.sleep)
        self.time_offset = 0

    def validUpdate(self, inputTime):
        return inputTime is not None and datetime.now() - inputTime < timedelta(seconds=3)

    def updateStatus(self, position=None, co2=None, data=None):
        if position is not None:
            self.positionReceived = datetime.now()
        if co2 is not None:
            self.co2Received = datetime.now()
        previous = self.zeroing
        if data is not None:
            self.zeroing = data.warming or data.zeroing
        if self.zeroing and not previous:
            self.led.blink()
        elif not self.zeroing and previous:
            self.led.solid()

    def updateLED(self):
        validPosition = self.validUpdate(self.positionReceived)
        validCo2 = self.validUpdate(self.co2Received)
        self.led.setColor([255 if validPosition and not validCo2 else 0,
                           255 if validPosition and validCo2 else 0,
                           255 if not validPosition and validCo2 else 0])
        self.s.enter(1, 1, self.updateLED, ())

    def callback(self, data):
        self.position = data
        self.updateStatus(position=True)

    def getDate(self):
        corrected_time = rospy.Time.now() + self.time_offset
        return datetime.fromtimestamp(corrected_time.secs + (corrected_time.nsecs/1e9))

    def co2Callback(self, data):
        self.updateStatus(co2=True, data=data)
        if self.position is not None:
            print("{} co2: {} {} {} {} {} {} {} {} @ {} {} {}".format(self.getDate(),
                                           data.ppm,
                                           data.sensor_temp,
                                           data.humidity,
                                           data.humidity_sensor_temp,
                                           data.atmospheric_pressure,
                                           data.detector_temp,
                                           data.source_temp,
                                           data.status,
                                           self.position.latitude,
                                           self.position.longitude,
                                           self.position.altitude))
        else:
            print("{} cos: {} {} {} {} {} {} {} {} @ -".format(self.getDate(),
                                            data.ppm,
                                            data.sensor_temp,
                                            data.humidity,
                                            data.humidity_sensor_temp,
                                            data.atmospheric_pressure,
                                            data.detector_temp,
                                            data.source_temp,
                                            data.status))

    def logCallback(self, data):
        print("{} LOG: {}".format(self.getDate(),data))

    def listener(self):

        # In ROS, nodes are uniquely named. If two nodes with the same
        # name are launched, the previous one is kicked off. The
        # anonymous=True flag means that rospy will choose a unique
        # name for our 'listener' node so that multiple listeners can
        # run simultaneously.
        rospy.init_node('gpslistener', anonymous=True)

        flight_computer_time = rospy.wait_for_message("{}/mavros/time_reference".format(self.id), TimeReference)
        self.time_offset = flight_computer_time.time_ref - rospy.Time.now()
        
        print("got time reference: {} diff: {} current: {}".format(flight_computer_time, self.time_offset, self.getDate()))
        rospy.Subscriber("{}/mavros/global_position/global".format(self.id), NavSatFix, self.callback)
        rospy.Subscriber("{}/co2".format(self.id), CO2, self.co2Callback)
        rospy.Subscriber("{}/log".format(self.id), String, self.logCallback)

        self.s.enter(1, 1, self.updateLED, ())
        self.s.run()

        # spin() simply keeps python from exiting until this node is stopped
        rospy.spin()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Log the given drone\'s GPS And CO2.')
    parser.add_argument('id', type=str, help='Name of the drone.')
    args = parser.parse_args()

    co2Logger(args.id).listener()
