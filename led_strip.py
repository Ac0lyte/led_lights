# This Class defines a generic control interface for a 12v LED strip.
# The led strip is controlled using 3 GPIO pins given on object creation.

# Improvements:
#
# - Create a list of "actions"
#   Move sunrise into the actions
#   stop_sunrise becomes stop_actions
#
# - Add an active() method
#   This returns the action name if any actions are currently running,
#   false if none are running.
#

import time
import math
import logging
import pigpio
from multiprocessing import Process

class led_strip:
    def __init__(self, red, green, blue, pwm_range = 100):
        self.red_pin = red
        self.green_pin = green
        self.blue_pin = blue
        self.pwm_range = pwm_range
        self.proc_sunrise = []

        self.pi = pigpio.pi()

        if self.pi.get_PWM_range(self.red_pin) != pwm_range:
            self.pi.set_PWM_range(self.red_pin, pwm_range)

        if self.pi.get_PWM_range(self.green_pin) != pwm_range:
            self.pi.set_PWM_range(self.green_pin, pwm_range)

        if self.pi.get_PWM_range(self.blue_pin) != pwm_range:
            self.pi.set_PWM_range(self.blue_pin, pwm_range)

        try:
            self.pwm_red = self.pi.get_PWM_dutycycle(self.red_pin)
        except:
            self.pi.set_PWM_dutycycle(self.red_pin, 0)
            self.pwm_red = self.pi.get_PWM_dutycycle(self.red_pin)

        try:
            self.pwm_green = self.pi.get_PWM_dutycycle(self.green_pin)
        except:
            self.pi.set_PWM_dutycycle(self.green_pin, 0)
            self.pwm_green = self.pi.get_PWM_dutycycle(self.green_pin)

        try:
            self.pwm_blue = self.pi.get_PWM_dutycycle(self.blue_pin)
        except:
            self.pi.set_PWM_dutycycle(self.blue_pin, 0)
            self.pwm_blue = self.pi.get_PWM_dutycycle(self.blue_pin)

        self.get()


    def set(self, red, green, blue):
        self.pi.set_PWM_dutycycle(self.red_pin, red)
        self.pi.set_PWM_dutycycle(self.green_pin, green)
        self.pi.set_PWM_dutycycle(self.blue_pin, blue)

        self.pwm_red = self.pi.get_PWM_dutycycle(self.red_pin)
        self.pwm_green = self.pi.get_PWM_dutycycle(self.green_pin)
        self.pwm_blue = self.pi.get_PWM_dutycycle(self.blue_pin)

        return self.get()


    def get(self):
        return (self.pwm_red, self.pwm_green, self.pwm_blue)


    def off(self):
        self.stop_sunrise()
        return self.set(self.pwm_range, self.pwm_range, self.pwm_range)


    def on(self):
        self.stop_sunrise()
        return self.set(0, 0, 0)


    def toggle(self):
        self.stop_sunrise()
        (r, g, b) = self.get()
        logging.debug(f'Toggle: r:{r}  g:{g}  b:{b}')
        if r < 255 or g < 255 or b < 255:
            self.off()
        else:
            self.on()


    def red(self):
        self.stop_sunrise()
        return self.set(0, self.pwm_range, self.pwm_range)


    def green(self):
        self.stop_sunrise()
        return self.set(self.pwm_range, 0, self.pwm_range)


    def blue(self):
        self.stop_sunrise()
        return self.set(self.pwm_range, self.pwm_range, 0)


    def background_sunrise(self, duration=600):
        logging.info('Starting background_sunrise')
        if len(self.proc_sunrise) > 0:
            logging.info('sunrise exists')
            if not self.proc_sunrise[0].is_alive():
                logging.info('sunrise is not alive')
                for x in self.proc_sunrise:
                    x.terminate()
                    x.join()
                self.proc_sunrise.clear()
                proc = Process(target=self.sunrise, args=(duration,))
                self.proc_sunrise.append(proc)
                self.proc_sunrise[0].start()
        else:
            logging.info('calling Process sunrise')
            proc = Process(target=self.sunrise, args=(duration, ))
            self.proc_sunrise.append(proc)
            self.proc_sunrise[0].start()


    def stop_sunrise(self):
        if len(self.proc_sunrise) > 0:
            self.proc_sunrise[0].terminate()
            self.proc_sunrise[0].join()
            self.proc_sunrise.clear()

    def sunrise(self, duration = 600):
        logging.info('Starting sunrise')
        self.sunrise = True
        pwm_range = self.pwm_range
        (red, green, blue) = self.get()
        step_adjustment = 1.449

        sleep = ((duration * step_adjustment) / (pwm_range * 3))

        sleep = sleep / 5
        for red in range(red, 0, -1):
            green = math.ceil(pwm_range - ((pwm_range - red) / 16))
            blue = math.ceil(pwm_range - ((pwm_range - green) / 15))
            self.set(red, green, blue)
            time.sleep(sleep)

        sleep = sleep * 5
        for green in range(green, 0, -1):
            blue = math.ceil(pwm_range - ((pwm_range - green) / 8))
            self.set(red, green, blue)
            time.sleep(sleep)

        for blue in range(blue, 0, -1):
            self.set(red, green, blue)
            time.sleep(sleep)

        self.sunrise = False
        logging.info("Sun's up!")


