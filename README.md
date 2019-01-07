# led_lights
random pieces of code for controlling RGB Led strips from a Raspberry PI

## api_server.py
Listens for api requests using the http protocol

current functions 
  - /on
  - /off
  - /toggle
  - /rgb
  - /sunset
  - /sunrise

## buttons.py
Watches for hardware button pushes. When a button push is detected it makes an API call.

# TODO
## General System
- Create systemd startup files
- Properly daemonize each piece
- Web UI with more control

## API Server
- Make the api server run under uWSGI and Nginx
- Make the light changes fade
- Make all API calls take an optional led set
- Clean out unused code
- Add a /leds endpoint that returns a list of led sets
- Save state when changes are made.
- Restore state on recovery from power loss
- Toggle between stored state and off
- Add swagger docs

## Button Monitor
- Make Sharon and Tim's buttons toggle each respective side
