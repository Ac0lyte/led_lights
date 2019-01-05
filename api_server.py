#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2018 Tim Schaller <TimSchaller@gmail.com>
#
# Distributed under terms of the GPL2 license.

"""
API server for led strip lights.
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
pwm_range = 255

leds = {}

leds['tim'] = led_strip(2, 3, 4, pwm_range)
leds['sharon'] = led_strip(17, 27, 22, pwm_range)

# Target time range to go from current levels to full on
time_to_full = 600


# ============================================================
# PIgpio
pi = pigpio.pi()


# Connect the buttons
# pi.callback(14, pigpio.RISING_EDGE, pigpio_callback)
# pi.callback(15, pigpio.RISING_EDGE, pigpio_callback)
# pi.callback(18, pigpio.RISING_EDGE, pigpio_callback)


# ============================================================
# Set up scheduler

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
    return "This is an api server.\n"


@app.route("/on")
def on():
    for led in leds:
        leds[led].on()
    return "Turn the lights on\n"


@app.route("/off")
def off():
    for led in leds:
        leds[led].off()
    return "Turn the lights off\n"


@app.route("/rgb")
def rgb():
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
    return "Set the lights color\n"


@app.route("/sunrise")
def sunrise():
    for led in leds:
        logging.info(f'Starting sunrise on [{led}]')
        leds[led].background_sunrise(time_to_full)
    return "Start the sunrise scheme\n"


@app.route("/schedule", methods=['GET', 'POST', 'DELETE'])
def schedule():
    if request.method == 'GET':
        ret = []
        for job in scheduler.get_jobs():
            temp_job = { 'id': job.id, 'name': job.name }
            ret.append(temp_job)
        return json.dumps(ret)

    elif request.method == 'POST':
        job = scheduler.add_job(tick, 'interval', seconds=3600)
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
        print('Tick! The time is: %s' % datetime.now())

def noop():
    return True

# ============================================================
# LED control functions
def sunrise(leds, duration=600):
    for key in leds:
        logging.info(f'Starting sunrise on [{key}]')
        leds[key].background_sunrise(duration)


def pigpio_callback(gpio, level, tick):
    logging.debug(f'callback {gpio} : {level} : {tick}')

    if "ticks" not in pigpio_callback.__dict__:
        pigpio_callback.ticks = {}

    if gpio not in pigpio_callback.ticks:
        pigpio_callback.ticks[gpio] = 0

    #if not hasattr(pigpio_callback.ticks, f'{gpio}'):
    #    pigpio_callback.ticks[f'{gpio}'] = 0

    if tick > (pigpio_callback.ticks[gpio] + 500000):
        old = pigpio_callback.ticks[gpio]
        logging.debug(f'OLD: {old}  NEW:{tick}')
        pigpio_callback.ticks[gpio] = tick

        if gpio == 14:
            logging.debug('Sunrise Requested')
            sunrise(leds)
        elif gpio == 15:
            logging.debug('Red Requested')
            for key in leds:
                leds[key].red()
        elif gpio == 18:
            logging.debug('Red Requested')
            for key in leds:
                leds[key].toggle()


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
print()
scheduler.add_job(noop)
print('------------------------------------------------------------')

scheduler.start()

print('============================================================')
print()

# jobs = scheduler.get_jobs()
# print('job list loaded')
# if len(jobs) < 2:
#     scheduler.add_job(tick, 'interval', seconds=30)
#     print('Added a new job')
# print('------------------------------------------------------------')


