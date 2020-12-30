# Spotify web API for Micropython
This is a library for using Spotify's web API from a IoT device with Micropython.
It was developed and tested with an esp8266, but the library was made to work on any device
and with both Micropython and CPython 3.5+. It is far from feature complete but there is 
a pattern to follow when adding more of the API. 

- spotify_web_api is the library
- main.py is the Seagulls! button example application
- boot.py is a template for setting up Wi-Fi
- wizard.py is a tool to set up the device
- spotify_web_api_micropython.bin is a Micropython v1.13 firmware for esp8266 with 
  the library frozen in it.