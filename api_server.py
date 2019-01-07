#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2018 Tim Schaller <TimSchaller@gmail.com>
#
# Distributed under terms of the GPL2 license.
#
# TODO:
# - define the LED stips (devices) in a config file
#   right now everything is hardcoded.
#

"""
API server for led strip lights.

This listens for API requests submitted over HTTP and interracts 
with one or more LED devices using the led_strip module.
"""
import sys

import select
import tty
import termios
import time
import logging
import math
import pigpio
import os
import json

from datetime import datetime

from multiprocessing import Process

from flask import Flask
from flask import jsonify
from flask import request

from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

from led_strip import led_strip

# ============================================================
# Logging

logging.basicConfig(level=logging.INFO,
                                       format='[%(levelname)s]  %(asctime)s - %(message)s',
                                       )


# ============================================================
# LED Strip(s)

# Set pwm range from 0 to 255
# Zero if full on 255 is full off
# TODO: Load these from a config file
pwm_range = 255

# Define the LED devices
leds = {}

# TODO: Load these from a config file
leds['tim'] = led_strip(2, 3, 4, pwm_range)
leds['sharon'] = led_strip(17, 27, 22, pwm_range)

# Target time range to go from current levels to full on
# when running the sunrise process.
# TODO: Load these from a config file
time_to_full = 600


# ============================================================
# PiGpio : Connect to the pgpiod daemon. Currently on the same host
# TODO: Allow multiple pigpio connections defined in a config file
pi = pigpio.pi()


# ============================================================
# Set up scheduler
# Currently using SQLite on localhost.
# Should I explore remote SQL servers? Overkill?
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
executors = {
    'default': ThreadPoolExecutor(5)
}
job_defaults = {
    'coalesce': True,
    'max_instances': 3
}


# ============================================================
# Set up Flask and flask routing

app = Flask(__name__)

@app.route("/")
def root():
    """
    The user reached root. This is a non used call.
    """
    return "This is an api server.\n"


@app.route("/on")
def on():
    """
    Turn on all the LED devices
    """

    ret = {}
    for led in leds:
        leds[led].on()
        ret[led] = leds[led].get()
    return jsonify(ret)


@app.route("/off")
def off():
    """
    Turn odd oll the LED devices
    """

    ret = {}
    for led in leds:
        leds[led].off()
        ret[led] = leds[led].get()
    return jsonify(ret)


@app.route("/state")
def state():
    """
    Return the state of all devices
    """

    ret = {}
    for led in leds:
        ret[led] = leds[led].get()
    return jsonify(ret)


@app.route("/toggle")
def toggle():
    """
    Toggle named/all LED devices between the current state and off
    """

    ret = {}
    if request.args.get('led'):
        led_in = request.args.get('led')
        if leds[led_in]:
            leds[led_in].toggle()
    else:
        led_sum = []
        for led in leds:
            led_sum.append(sum(leds[led].get()))
       
        for led in leds:
            if min(led_sum) == max(led_sum) :
                leds[led].toggle()
            else:
                leds[led].off()

        ret[led] = leds[led].get()
    return jsonify(ret)


@app.route("/rgb")
def rgb():
    """
    Set the LED devices to a specific color.

    The color is defined by red, green, and blue values.
    Use the current values for any colors not given.
    """

    ret = {}
    if request.args.get('red'):
        red_in = request.args.get('red')
    else:
        red_in = None

    if request.args.get('blue'):
        blue_in = request.args.get('blue')
    else:
        blue_in = None

    if request.args.get('green'):
        green_in = request.args.get('green')
    else:
        green_in = None

    for led in leds:
        if red_in is None:
            red = leds[led].get_red()
        else: 
            red = red_in

        if blue_in is None:
            blue = leds[led].get_blue()
        else: 
            blue = blue_in

        if green_in is None:
            green = leds[led].get_green()
        else: 
            green = green_in

        print("red: {}  green: {}  blue: {}".format(red, green, blue))

        leds[led].set(red, blue, green)
        ret[led] = leds[led].get()
    return jsonify(ret)


@app.route("/sunrise")
def sunrise():
    """
    Run the sunrise routine/action on all devices.
    """

    ret = {}
    for led in leds:
        logging.info(f'Starting sunrise on [{led}]')
        leds[led].background_sunrise(time_to_full)
        ret[led] = leds[led].get()
    return jsonify(ret)


@app.route("/schedule", methods=['GET', 'POST', 'DELETE'])
def schedule():
    if request.method == 'GET':
        ret = []
        for job in scheduler.get_jobs():
            temp_job = { 'id': job.id, 'name': job.name }
            ret.append(temp_job)
        return json.dumps(ret)

    elif request.method == 'POST':
        action = request.values['action']
        frequency = int(request.values['freq'])

        if action == 'tick':
            job = scheduler.add_job(tick, 'interval', seconds=frequency)
        elif action == 'on':
            job = scheduler.add_job(on, 'interval', seconds=frequency)
        elif action == 'off':
            job = scheduler.add_job(off, 'interval', seconds=frequency)
        else:
            return "I do not know how to do that.\n"

        temp_job = { 'id': job.id, 'name': job.name }
        return json.dumps(temp_job)

    elif request.method == 'DELETE':
        ret = []
        for job in scheduler.get_jobs():
            temp_job = { 'id': job.id, 'name': job.name }
            ret.append(temp_job)
            job.remove()
        return json.dumps(ret)

    return "I do not know how to do that.\n"


@app.route("/schedule/<event_id>", methods=['GET', 'PUT', 'DELETE'])
def schedules(event_id):
    """
    Interract with the scheduler.
    """

    if request.method == 'GET':
        return f"GET event with id {event_id}\n"
    elif request.method == 'PUT':
        return f"UPDATE event with id {event_id}\n"
    elif request.method == 'DELETE':
        return f"DELETE event with id {event_id}\n"

    return "I do not know how to do that.\n"



# ============================================================
# Basic do nothing unit of work

def tick():
    """
    Print a message for the log
    """

    print('Tick! The time is: %s' % datetime.now())

def noop():
    """
    Do nothing, return True
    """

    return True

# ============================================================
# LED control functions
#def sunrise(leds, duration=600):
#    for key in leds:
#        logging.info(f'Starting sunrise on [{key}]')
#        leds[key].background_sunrise(duration)


# ============================================================
# Create the scheduler. 
# 
# The initial noop job is top force the scheduler to load the
# jobstore from disk.
#
# The tick job is so that a job exists for testing purposes
# and can be removed when I am satisfied with the functionality
# of this system.
#
 
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc)

logging.info('')
scheduler.add_job(noop)

logging.info('------------------------------------------------------------')

scheduler.start()

logging.info('============================================================')
logging.info('')


if __name__ == "__main__":
        app.run()

