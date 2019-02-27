#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2019 Tim Schaller <timschaller@gmail.com>
#
# Distributed under terms of the GPLv2 license.
#
# TODO: 
#  - Remove hardcoded URL and load from config file.
#  - Define the buttons in a confile
#  - Define the actions from a config file
#  - Turn this into a proper daemon (python-daemon?)

"""
Responds to hardware button pushes with API calls

This is a quick and dirty hardware monitor with everything hardcoded.
It was created for a custom headbaord with intergrated LED lights
controlled by a Raspberry Pi. Overkill but fun.  };->

Refactoring would be nice, but will wait untill it is really warranted.
This might be if/when additional buttons get added to the system.
"""

import sys
import time
import pigpio
import requests
import logging

# ============================================================
# Logging

logging.basicConfig(level=logging.INFO,
                   format='[%(levelname)s]  %(asctime)s - %(message)s',
                   )



def do_watcher():
    """
    Watch for button pushes and respond with http API calls."
    """

    pi = pigpio.pi()
    if not pi.connected:
           exit()

    debounce = 1000

    pi.set_mode(13, pigpio.INPUT)
    pi.set_glitch_filter(13, debounce)
    cb1 = pi.callback(13, pigpio.RISING_EDGE, button_main)

    pi.set_mode(6, pigpio.INPUT)
    pi.set_glitch_filter(6, debounce)
    cb2 = pi.callback(6, pigpio.RISING_EDGE, button_red)

    pi.set_mode(19, pigpio.INPUT)
    pi.set_glitch_filter(19, debounce)
    cb3 = pi.callback(19, pigpio.RISING_EDGE, button_white)

    pi.set_mode(26, pigpio.INPUT)
    pi.set_glitch_filter(26, debounce)
    cb4 = pi.callback(26, pigpio.RISING_EDGE, button_sharon)

    pi.set_mode(5, pigpio.INPUT)
    pi.set_glitch_filter(5, debounce)
    cb5 = pi.callback(5, pigpio.RISING_EDGE, button_tim)

    logging.info("PiGPIO Conected");

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        cb1.cancel()
        cb2.cancel()
        cb3.cancel()
        cb4.cancel()
        cb5.cancel()


def button_main(gpio, level, tick):
    """CALLBACK:  Respond when the main button is pressed """

    logging.info("button main pressed")
    r = requests.get('http://127.0.0.1:5000/toggle')
    return r


def button_red(gpio, level, tick):
    """CALLBACK:  Respond when the red button is pressed """

    logging.info("button red pressed")
    r = requests.get('http://127.0.0.1:5000/rgb?red=0&blue=255&green=255')
    return r


def button_white(gpio, level, tick):
    """CALLBACK:  Respond when the white button is pressed """

    logging.info("button white pressed")
    r = requests.get('http://127.0.0.1:5000/rgb?red=0&blue=0&green=0')
    return r


def button_sharon(gpio, level, tick):
    """ Respond when the sharon button is pressed """

    logging.info("CALLBACK: button sharon pressed")
    r = requests.get('http://127.0.0.1:5000/toggle?led=sharon')
    return r
    return True


def button_tim(gpio, level, tick):
    """ CALLBACK: Respond when the tim button is pressed """

    logging.info("button tim pressed")
    r = requests.get('http://127.0.0.1:5000/toggle?led=tim')
    return r


if __name__ == "__main__":
    logging.info ("Starting button watcher");
    do_watcher()
