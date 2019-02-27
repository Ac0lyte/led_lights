# This Class defines a generic control interface for a 12v LED strip.
# The led strip is controlled using 3 GPIO pins per strip 
# that are given on led strip object creation.
#
# Copyright 2018 Tim Schaller <timschaller@gmail.com>
# All rights reserved
#
# Released to the public under the GPLv3 license

# Improvements that may never get done
# (come on this is a personal home project ):
#
# - Create a list of "actions"
#   This should allow for a better method to expand the 
#   differnt lighting schemes as they become needed/wanted.
#   This will include 
#   - Move sunrise into the actions
#   - Move fade into the actions
#   - Combine stop_sunrise and stop_fade to become stop_actions
#
# - Add an active() method
#   This returns the action name if any actions are currently running,
#   false if none are running.
#
# - Huntdown all hardcoded assumption and make then configurable
#   Know assumptions are:
#    - PWM limits of 0 as on  and 255 as off
#    - pigpio daemon is on local server
#
# - Allow global fade_duration to be set by the user
#
# - Allow rempte PI to be used in pigpio init

"""Control an RGB LED strip on a Raspberry Pi"""

import time
import math
import logging
import pigpio
from multiprocessing import Process


class led_strip:
    """
    This Class defines a generic control interface for a 12v LED strip.
    
    The led strip is controlled using 3 GPIO pins per strip 
    that are given on led strip object creation.
    """
       
    def __init__(self, red, green, blue, pwm_range = 100, fade_duration = 1):
        """
        Object initialzation. Arguements are 
        pins for red, green, blue PWM chanels,
        maximum pwm value to send,
        length of time to fade between transitions in seconds.
        """

        # Capture the given control pins
        self.red_pin = red
        self.green_pin = green
        self.blue_pin = blue

        # Set the pwm_range, and use it as a placeholder for color settings
        self.pwm_range = pwm_range
        self.pwm_red = pwm_range
        self.pwm_green = pwm_range
        self.pwm_blue = pwm_range

        # Set defaults for previous state. 0 = full on"
        self.old_red = 0
        self.old_green = 0
        self.old_blue = 0

        # Capture given transition fade time in seconds
        self.fade_duration = fade_duration

        # Set up lists to capture action processes
        # TODO: Combine into common generic actions
        self.proc_fade = []
        self.proc_sunrise = []

        # Initilize PiGPIO interface
        self.pi = pigpio.pi()

        # Set initial state to off (max pwm_range)
        # TODO: Save state to disk on changes and 
        # if state file exists, restore on start up
        if self.pi.get_PWM_range(self.red_pin) != pwm_range:
            self.pi.set_PWM_range(self.red_pin, pwm_range)

        if self.pi.get_PWM_range(self.green_pin) != pwm_range:
            self.pi.set_PWM_range(self.green_pin, pwm_range)

        if self.pi.get_PWM_range(self.blue_pin) != pwm_range:
            self.pi.set_PWM_range(self.blue_pin, pwm_range)

        # Get current state. Set one if it does not exist.
        # I know that this looks redundent ... basically it
        # sets any color to full on if it can not read it's value
        # from the pigpio daemon. This means that if the lights
        # come on at boot there is an error using the pigpio
        # This will become confusing with persistent state
        #
        # Update: Now they set themselved to off... 
        try:
            self.pwm_red = self.pi.get_PWM_dutycycle(self.red_pin)
        except:
            self.pi.set_PWM_dutycycle(self.red_pin, pwm_range)
            self.pwm_red = self.pi.get_PWM_dutycycle(self.red_pin)

        try:
            self.pwm_green = self.pi.get_PWM_dutycycle(self.green_pin)
        except:
            self.pi.set_PWM_dutycycle(self.green_pin, pwm_range)
            self.pwm_green = self.pi.get_PWM_dutycycle(self.green_pin)

        try:
            self.pwm_blue = self.pi.get_PWM_dutycycle(self.blue_pin)
        except:
            self.pi.set_PWM_dutycycle(self.blue_pin, pwm_range)
            self.pwm_blue = self.pi.get_PWM_dutycycle(self.blue_pin)

        # Get and return the current state in a standard format
        self.get()


    def direct_set(self, red, green, blue):
        """
        Set the led state immedieatly.
        
        This is done without any fading or any attempt to stop actions.
        This is what the actions should call. 
        Do not call this from external code as it does not ensure
        that actions are stopped first.
        """
        
        self.pi.set_PWM_dutycycle(self.red_pin, red)
        self.pi.set_PWM_dutycycle(self.green_pin, green)
        self.pi.set_PWM_dutycycle(self.blue_pin, blue)
        self.pwm_red = red
        self.pwm_green = green
        self.pwm_blue = blue


    def set(self, red, green, blue, kill_procs = True):
        """
        Set the LED state using fade. Kill all running actions.

        Actions should NOT use this. Use direct_state instead.
        This uses the  background fade action. This is to allow
        multiple strips to fade to the desired state all at once.
        """

        if kill_procs :
            # TODO: Combine these into a generic actions
            self.stop_fade()
            self.stop_sunrise()

        self.pwm_red = self.pi.get_PWM_dutycycle(self.red_pin)
        self.pwm_green = self.pi.get_PWM_dutycycle(self.green_pin)
        self.pwm_blue = self.pi.get_PWM_dutycycle(self.blue_pin)

        return self.background_fade(red, green, blue)


    def background_fade(self, red, green, blue):
        """
        Run fade in the backgroud, allowing the main process to continue."
        
        Call this, do not call fade directly.

        TODO: Combile this with background_sunrise() into
            : a generic background_action() method and make this 
            : a wrapper for that
        """

        logging.info('Starting background_fade')
        if len(self.proc_fade) > 0:
            logging.info('fade exists')
            if not self.proc_fade[0].is_alive():
                logging.info('fade is not alive')
                for x in self.proc_fade:
                    x.terminate()
                    x.join()
                self.proc_fade.clear()
                proc = Process(target=self.fade, args=(red, green, blue,))
                self.proc_fade.append(proc)
                self.proc_fade[0].start()
        else:
            logging.info('calling Process fade')
            proc = Process(target=self.fade, args=(red, green, blue,))
            self.proc_fade.append(proc)
            self.proc_fade[0].start()


    def stop_fade(self):
        """
        Stop any fade actions.
        """

        if len(self.proc_fade) > 0:
            self.proc_fade[0].terminate()
            self.proc_fade[0].join()
            self.proc_fade.clear()


    def fade(self, red, green, blue):
        """
        Fade the device from the current state to the desired state.

        This transitions from the current state to the desired state
        by changing each color value in increments and pausing between
        each change.

        This is a blocking process. It is HIGHLY recommended that you
        use background_fade instead, unless you really want to stop
        responding to the users for up to a the full fade_duration.

        Note: Because this is normally run in the background on a child
        process all updates of the pwm color values do not get propigated
        to the parent process. They are lost until the parent decides to 
        update them.
        """
        logging.debug(f'Fade to: r:{red}  g:{green}  b:{blue}')
        while int(red) != self.pwm_red or int(green) != self.pwm_green or int(blue) != self.pwm_blue:
            if int(red) > self.pwm_red :
                r = self.pwm_red + 1
            elif int(red) < self.pwm_red :
                r = self.pwm_red - 1
            else : 
                r = self.pwm_red

            if int(green) > self.pwm_green :
                g = self.pwm_green + 1
            elif int(green) < self.pwm_green :
                g = self.pwm_green - 1
            else : 
                g = self.pwm_green

            if int(blue) > self.pwm_blue :
                b = self.pwm_blue + 1
            elif int(blue) < self.pwm_blue :
                b = self.pwm_blue - 1
            else : 
                b = self.pwm_blue

            self.direct_set(r, g, b)

            time.sleep(self.fade_duration / self.pwm_range)

        # Paranoia: The device should already be in this state,
        # but I'm willing to burn a few cycles to ensure it is
        # just in case.
        self.direct_set(red, green, blue)
        return self.get()


    def get(self):
        """
        Return the current pwm color values.

        Due to the fact that the action child processes do not 
        update the internl state values of their parents This
        updates the stored state from reality prior to 
        returning the stored state.
        """

        self.pwm_red = self.pi.get_PWM_dutycycle(self.red_pin)
        self.pwm_green = self.pi.get_PWM_dutycycle(self.green_pin)
        self.pwm_blue = self.pi.get_PWM_dutycycle(self.blue_pin)
        return (self.pwm_red, self.pwm_green, self.pwm_blue)


    def get_red(self):
        """
        Returns the pwm state of the red channel
        """

        self.pwm_red = self.pi.get_PWM_dutycycle(self.red_pin)
        return (self.pwm_red)


    def get_green(self):
        """
        Returns the pwm state of the green channel
        """

        self.pwm_green = self.pi.get_PWM_dutycycle(self.green_pin)
        return (self.pwm_green)


    def get_blue(self):
        """
        Returns the pwm state of the blue channel
        """

        self.pwm_blue = self.pi.get_PWM_dutycycle(self.blue_pin)
        return (self.pwm_blue)


    def off(self):
        """
        Store the current state then turn the device off.
        """

        (self.old_red, self.old_green, self.old_blue) = self.get()
        return self.set(self.pwm_range, self.pwm_range, self.pwm_range)


    def on(self):
        """
        Store the current state then turn the device on.
        """

        (self.old_red, self.old_green, self.old_blue) = self.get()
        return self.set(0, 0, 0)


    def toggle(self):
        """
        Switch the device between the current state and off.
        
        Note that id the old state gets set to off then this does nothing.    
        """

        (r, g, b) = self.get()
        logging.debug(f'Toggle: r:{r}  g:{g}  b:{b}')
        if r < 255 or g < 255 or b < 255:
            (self.old_red, self.old_green, self.old_blue) = self.get()
            self.off()
        else:
            self.set(self.old_red, self.old_green, self.old_blue)


    def red(self):
        """
        Set the device to shoe only red
        """

        return self.set(0, self.pwm_range, self.pwm_range)


    def green(self):
        """
        Set the device to shoe only green
        """

        return self.set(self.pwm_range, 0, self.pwm_range)


    def blue(self):
        """
        Set the device to shoe only blue
        """

        return self.set(self.pwm_range, self.pwm_range, 0)


    def background_sunrise(self, duration=600):
        """
        Run the sunrise action in a background process.

        Call this, do not call sunrise directly.

        TODO: Combile this with background_fade() into
            : a generic background_action() method and make this 
            : a wrapper for that
        """

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
        """
        Stop all sunrise background processes.

        TODO: Combine this with stop_fade() into stop_action()
        """

        if len(self.proc_sunrise) > 0:
            self.proc_sunrise[0].terminate()
            self.proc_sunrise[0].join()
            self.proc_sunrise.clear()


    def sunrise(self, duration = 600):
        """
        Runs the sunrise scene.

        This is a blocking process, Do not run it directly unless
        you want to ignore ALL user input for 10 minutes or more.

        DO NOT CALL DIRECTLY use background_sunrise()
        """

        logging.info('Starting sunrise')
        self.sunrise = True
        pwm_range = self.pwm_range
        (red, green, blue) = self.get()
        step_adjustment = 1.449

        sleep = ((duration * step_adjustment) / (pwm_range * 3))

        sleep = sleep / 5
        logging.info("Sunrise - red dawn")
        for red in range(red, 0, -1):
            green = math.ceil(pwm_range - ((pwm_range - red) / 16))
            blue = math.ceil(pwm_range - ((pwm_range - green) / 15))
            self.direct_set(red, green, blue)
            time.sleep(sleep)

        sleep = sleep * 5
        logging.info("Sunrise - brighten")
        for green in range(green, 0, -1):
            blue = math.ceil(pwm_range - ((pwm_range - green) / 8))
            self.direct_set(red, green, blue)
            time.sleep(sleep)

        for blue in range(blue, 0, -1):
            self.direct_set(red, green, blue)
            time.sleep(sleep)

        self.sunrise = False
        logging.info("Sun's up!")


