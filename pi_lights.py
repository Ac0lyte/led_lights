#!/usr/bin/python

# lights.py
# Written to control two 12v LED strips (5050) from a Raspbery PI
# This depends on the pigpio daemin and library, which can be 
# found at: http://abyz.me.uk/rpi/pigpio


import sys

import select
import tty
import termios
import time
import logging
import math
import pigpio

from multiprocessing import Process
from apscheduler.schedulers.background import BackgroundScheduler
from led_strip import led_strip
# import switches

logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s]  %(asctime)s - %(message)s',
                    )

scheduler = BackgroundScheduler({
    'apscheduler.jobstores.default': {
            'type': 'sqlalchemy',
            'url': 'sqlite:///jobs.sqlite'
        },
    'apscheduler.job_defaults.coalesce': 'false',
    'apscheduler.job_defaults.max_instances': '3',
})


# led_strips
leds = {}

def main(argv):
    logging.info(f'Starting {argv[0]}')

    # Init the led strip(s)

    # Set pwm range from 0 to 255
    # Zero if full on 255 is full off
    pwm_range = 255

    # LED Strip on Tim's side of the bed
    leds['tim'] = led_strip(2, 3, 4, pwm_range)
    leds['sharon'] = led_strip(17, 27, 22, pwm_range)


    # Target time range to go from current levels to full on
    time_to_full = 600
   
    pi = pigpio.pi()

    # Connect the buttons
    # pi.callback(14, pigpio.RISING_EDGE, pigpio_callback)
    # pi.callback(15, pigpio.RISING_EDGE, pigpio_callback)
    # pi.callback(18, pigpio.RISING_EDGE, pigpio_callback)

    for key in leds:
        led = leds[key]
        led.red()
        time.sleep(0.2)
        led.green()
        time.sleep(0.2)
        led.blue()
        time.sleep(0.2)
        led.off()


    logging.info(f'{argv[0]} is ready.')
    
    def isData():
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])
   
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())

        i = 0
        on = False
        while 1:

            i += 1
            if isData():
                c = sys.stdin.read(1)
                if c == '\x1b':         # x1b is ESC
                    logging.info('Escape Requested')
                    for key in leds:
                        leds[key].stop_sunrise()
                    break
                elif c == 'o':
                    logging.info('On/Off Requested')
                    for key in leds:
                        leds[key].toggle()

                elif c == 'r':
                    logging.info('Red Requested')
                    for key in leds:
                        leds[key].red()
                    on = True

                elif c == 's':
                    logging.info('Sunrise Requested')
                    sunrise(leds, time_to_full)
                    on = True

                else:
                    print(i)

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


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


if __name__ == "__main__":
        main(sys.argv)
