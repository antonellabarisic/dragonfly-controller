#!/bin/bash
rosrun dragonfly announce.py dragonfly1 &
rosrun dragonfly announce.py intruder2 &
rosrun dragonfly command.py dragonfly1 &
rosrun dragonfly command.py intruder2