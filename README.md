# open_echo
An ongoing open-source project is about building an open-source sonar for bathymetry and research.

### Currently in development. Not ready for external use!

# Current state
- partially reverse-engineered "LUCKY Fish Finder"
- get raw data from echo receiver/amplifier to FastLOGIC/Arduino
- plot data in a waterfall chart using Matplotlib + Python
- DIY transducer built and tested (works)

The LUCKY fishfinder with a DIY transducer (or stock) RAW amplifier (echo) data can be read using an Arduino, and data can be displayed using Matplotlib + Python.

Relevant pins on the LUCKY fish finder:
<img alt="LUCKY fishfinder pin hack" src="/reverse_engineering/images/fishfinder_pins.jpg">

Measured results using LUCKY fishfinder, FastLOGIC (Arduino) and Matplotlib + Python:
<img alt="LUCKY fishfinder pin hack" src="/reverse_engineering/images/echo_capture.jpg">

The chart shows a measurement of reflection time (translated to cm using 1482m/s speed of sound in water) and the past 50 measurements. The LUCKY fish finder takes around 2.3 full measurements per second. The brigter the pixel, the stronger the return signal. The plot shows the sandy ground in the first 1/4 and the rest is the reflection of a metal ladder in the water (horizontal).


# Video
[![LINK TO VIDEO](https://img.youtube.com/vi/UDYWQIizN7A/0.jpg)](https://www.youtube.com/watch?v=UDYWQIizN7A)

# Useful Links
https://i.sstatic.net/FSXvI.jpg 
 
https://tomeko.net/projects/dso138/index.php?lang=en 
 
https://github.com/ardyesp/DLO-138 
 
https://www.rapp-instruments.de/RemoteSensing/Roves/sidescan/sidescan.htm 

# Shopping list
 Transducer: https://de.aliexpress.com/item/1005006777922084.html
 
 DSO138 Oscilloscope with STM32: https://de.aliexpress.com/item/1005006777922084.html
 
 Lucky Fishfinder: https://de.aliexpress.com/item/32711659077.html

