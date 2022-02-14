#!/usr/bin/env python
import math
import numpy as np
from enum import Enum

import pulp
from dragonfly_messages.msg import LatLon
from geometry_msgs.msg import PoseStamped, Point, Quaternion


class Span(Enum):
    WALK = 1
    RANGE = 2


def createWaypoint(x, y, altitude, orientation):
    waypoint = PoseStamped()
    waypoint.pose.position.x = x
    waypoint.pose.position.y = y
    waypoint.pose.position.z = altitude
    waypoint.pose.orientation.z = orientation.z
    waypoint.pose.orientation.w = orientation.w

    return waypoint


def calculateRange(type, start, end, length):
    if type == Span.WALK:
        waypoints = []
        deltax = end.x - start.x
        deltay = end.y - start.y
        deltaz = end.z - start.z
        distance = math.sqrt((deltax * deltax) + (deltay * deltay) + (deltaz * deltaz))
        for i in range(1, int(distance / length) + 1):
            waypoints.append(Point(start.x + (i * length * deltax / distance),
                                   start.y + (i * length * deltay / distance),
                                   start.z + (i * length * deltaz / distance)))
        return waypoints
    elif type == Span.RANGE:
        return [end]


def buildRelativeWaypoint(localposition, position, waypoint, altitude, orientation):
    earthCircumference = 40008000
    return createWaypoint(
        localposition.x - ((position.longitude - waypoint.longitude) * (earthCircumference / 360) * math.cos(
            position.latitude * 0.01745)),
        localposition.y - ((position.latitude - waypoint.latitude) * (earthCircumference / 360)),
        altitude,
        orientation
    )


def createLatLon(localwaypoint, localposition, position):
    earthCircumference = 40008000
    latitude = position.latitude - (localposition.y - localwaypoint.y) * 360 / earthCircumference
    longitude = position.longitude - (localposition.x - localwaypoint.x) * 360 / (
                earthCircumference * math.cos(latitude * 0.01745))

    return LatLon(latitude=latitude, longitude=longitude, relativeAltitude=localwaypoint.z)


def build3DDDSAWaypoints(rangeType, stacks, size, index, loops, radius, stepLength):
    waypoints = []
    toggleReverse = False
    for stack in range(0, stacks):

        ddsaWaypoints = buildDDSAWaypoints(rangeType, stack, size, index, loops, radius, stepLength)
        if toggleReverse:
            ddsaWaypoints = ddsaWaypoints[::-1]
        waypoints = waypoints + ddsaWaypoints

        toggleReverse = not toggleReverse

    return waypoints

def buildDDSAWaypoints(rangeType, altitude, size, index, loops, radius, stepLength):

    waypoints = []
    start = Point(-(index * radius), 0, altitude)
    waypoints.append(start)
    previous = start
    for loop in range(loops):
        for corner in range(4):

            xoffset = loop * size + index + 1
            yoffset = xoffset
            if corner == 0:
                xoffset = -size * loop - index
            if corner == 2 or corner == 3:
                yoffset = -yoffset
            if corner == 3:
                xoffset = -xoffset - (size - 1)
                # Ends loop square with the last corner
                if loop == loops - 1:
                    xoffset += index  + 1


            next = Point(xoffset, yoffset, altitude)

            for waypoint in calculateRange(rangeType, previous, next, stepLength):
                waypoints.append(Point(waypoint.x * radius, waypoint.y * radius, waypoint.z))

            previous = next

    return waypoints


def linearXRange(points, setY, type):
    problem = pulp.LpProblem('range', type)

    x = pulp.LpVariable('x', cat='Continuous')
    y = pulp.LpVariable('y', cat='Continuous')

    # Objective function
    problem += x

    def buildLineEquation(index1, index2):
        a = -(points[index2][1] - points[index1][1])
        b = points[index2][0] - points[index1][0]
        c = (a * points[index1][0]) + (b * points[index1][1])
        # print('(', a, 'x+',b,'y >=',c,'),')
        return (a * x) + (b * y) >= c

    for i in range(1, len(points)):
        problem += buildLineEquation(i - 1, i)

    problem += buildLineEquation(len(points) - 1, 0)

    problem += y == setY

    # print problem
    pulp.GLPK_CMD(msg=0).solve(problem)

    return x.value()


def linearYRange(points, type):
    problem = pulp.LpProblem('range', type)

    x = pulp.LpVariable('x', cat='Continuous')
    y = pulp.LpVariable('y', cat='Continuous')

    # Objective function
    problem += y

    def buildLineEquation(index1, index2):
        a = -(points[index2][1] - points[index1][1])
        b = points[index2][0] - points[index1][0]
        c = (a * points[index1][0]) + (b * points[index1][1])
        # print('(', a, 'x+',b,'y >=',c,'),')
        return (a * x) + (b * y) >= c

    for i in range(1, len(points)):
        problem += buildLineEquation(i - 1, i)

    problem += buildLineEquation(len(points) - 1, 0)

    # print problem
    pulp.GLPK_CMD(msg=0).solve(problem)

    return y.value()


def build3DLawnmowerWaypoints(rangeType, altitude, localPosition, position, stacks, boundary, stepLength, orientation):
    waypoints = []
    toggleReverse = False
    for stack in range(0, stacks):

        lawnmowerWaypoints = buildLawnmowerWaypoints(rangeType, altitude + stack, localPosition, position, boundary,
                                                     stepLength, orientation)
        if toggleReverse:
            lawnmowerWaypoints = lawnmowerWaypoints[::-1]
        waypoints = waypoints + lawnmowerWaypoints

        toggleReverse = not toggleReverse

    return waypoints


def buildLawnmowerWaypoints(rangeType, altitude, localposition, position, boundary, stepLength, orientation):
    boundary_meters = []

    waypoints = []

    for waypoint in boundary:
        goalPos = buildRelativeWaypoint(localposition, position, waypoint, altitude, orientation)

        boundary_meters.append((goalPos.pose.position.x, goalPos.pose.position.y))

    # Get minimum in Y dimension
    miny = linearYRange(boundary_meters, pulp.LpMinimize)
    # Get maximum in Y dimension
    maxy = linearYRange(boundary_meters, pulp.LpMaximize)

    print("miny:{} maxy:{} ".format(miny, maxy))

    stepdirection = 1 if miny < maxy else -1

    for y in range(int(math.ceil(miny)), int(math.floor(maxy)), int(2 * stepLength)):
        minx = linearXRange(boundary_meters, y, pulp.LpMinimize)
        maxx = linearXRange(boundary_meters, y, pulp.LpMaximize)
        print("minx:{} maxx:{} ".format(minx, maxx))
        waypoints.append(createWaypoint(minx, y, altitude, orientation))
        for point in calculateRange(rangeType, Point(minx, y, altitude), Point(maxx, y, altitude), stepLength):
            waypoints.append(createWaypoint(point.x, point.y, point.z, orientation))
        minx = linearXRange(boundary_meters, y + stepLength, pulp.LpMinimize)
        maxx = linearXRange(boundary_meters, y + stepLength, pulp.LpMaximize)
        print("minx:{} maxx:{} ".format(minx, maxx))
        waypoints.append(createWaypoint(maxx, y + stepLength, altitude, orientation))
        for point in calculateRange(rangeType, Point(maxx, y + (stepdirection * stepLength), altitude),
                                    Point(minx, y + (stepdirection * stepLength), altitude), stepLength):
            waypoints.append(createWaypoint(point.x, point.y, point.z, orientation))

    return waypoints

def get_quaternion_from_euler(roll, pitch, yaw):
    """
    Convert an Euler angle to a quaternion.

    Input
    :param roll: The roll (rotation around x-axis) angle in radians.
    :param pitch: The pitch (rotation around y-axis) angle in radians.
    :param yaw: The yaw (rotation around z-axis) angle in radians.

    Output
    :return qx, qy, qz, qw: The orientation in quaternion [x,y,z,w] format
    """
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)

    data = Quaternion()
    data.x = qx
    data.y = qy
    data.z = qz
    data.w = qw

    return data
