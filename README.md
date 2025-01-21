# open_echo
An ongoing open-source project about building a sonar for bathymetry and research.

The TUSS4470 Arduino PCB can be used to test different frequencies and transducer types. The Python script lets you see the echoes in a waterfall chart.

### Currently in development. Almost ready for external use!

# Current state
- partially reverse-engineered "LUCKY Fish Finder"
- get raw data from echo receiver/amplifier to FastLOGIC/Arduino
- plot data in a waterfall chart using Matplotlib + Python
- DIY transducer built and tested (works)
- TUSS4470 board built and tested (works)
- TUSS4470 Arduino code example done

The LUCKY fishfinder with a DIY transducer (or stock) RAW amplifier (echo) data can be read using an Arduino, and data can be displayed using Matplotlib + Python. The new (January 2025) TUSS4470 board is now able to use transducers (40kHz and 200kHz tested), drive them, receive echos, filter the signal and send the RAW echo data to the (same) Python backend.
  
  
The LUCKY fishfinder hack is pretty much obsolte and replaced by the TUSS4470 board. If you want to play with custom sonar, use this!
--------
# TUSS4470 Ultrasonic Transducer Driver Arduino Board
This [PCB-board](hardware/TUSS4470_shield) is an Arduino (Uno) compatible board to test the Texas Instruments TUSS4470 Ultrasonic driver IC. The provided example [code](software/tuss4470_test/tuss4470_test.ino) lets you drive a 40kHz transducer, apply noise filtering, and send the echo via Serial to the [Python backend](software/development/python/main.py). You can change the code to your needs (i.e. to use other frequencies, sample sizes, speed etc.). The Arduino UNOs clock speed and RAM size limits the sampling speed to a resolution of ca. 2cm in air and 8cm under water and to ca. 500 Samples. An Arduino MEGA should solve this issue.

TUSS4470 Arduino Shield:
<img alt="PCB overview TUSS4470" src="/TUSS4470_shield_001/TUSS4470_shield_hardware/images/assembly2.jpg">

<img alt="PCB overview TUSS4470" src="/TUSS4470_shield_001/TUSS4470_shield_hardware/images/top.jpg">

<img alt="PCB overview TUSS4470" src="/TUSS4470_shield_001/TUSS4470_shield_hardware/images/whole_setup.jpg">




The TUSS4470 works as follows:
After initial setup, a burst of 8 pulses in drive frequency is sent to the TUSS4470 by the Arduino on PIN9. The TUSS4470 sends this pulse to the transducer then waits. The Transducer sends this pulse out as a short pulse of sound. Echos reflected by obstacles bounce back to the transducer and excite a voltage in it. The TUSS4470 measures that voltage, filters it, amplifies it and sends it to the A0 pin of the Arduino. By reading this amplified voltage, an (or multiple) obstacles can be detected. The Python script plots this data in a waterfall diagram.


<img alt="PCB overview TUSS4470" src="/TUSS4470_shield_001/TUSS4470_shield_hardware/images/echos.jpg">

--------
# LUCKY Fishfinder Hack
Relevant pins on the LUCKY fish finder:
<img alt="LUCKY fishfinder pin hack" src="/reverse_engineering/images/fishfinder_pins.JPG">

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

https://www.youtube.com/watch?v=ZtUkt8Q4EJE

# Shopping list
 Transducer: https://de.aliexpress.com/item/1005006007865920.html
 
 DSO138 Oscilloscope with STM32: https://de.aliexpress.com/item/1005006777922084.html
 
 Lucky Fishfinder: https://de.aliexpress.com/item/32711659077.html


 # THANK YOU FOR SUPPORT!
 www.kogger.tech

