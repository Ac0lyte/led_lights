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
    return "Turn the lights on\n"


@app.route("/off")
def off():
    return "Turn the lights off\n"


@app.route("/rgb")
def rgb():
    return "Set the lights color\n"


@app.route("/sunrise")
def sunrise():
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
        job = scheduler.add_job(tick, 'interval', seconds=30)
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


