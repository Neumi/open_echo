# Open Echo SONAR
An ongoing open-source project about building a sonar for bathymetry and research.

The TUSS4470 Arduino PCB can be used to test different frequencies and transducer types. The Python script lets you see the echoes in a waterfall chart.

### Currently in development. TUSS4470 development shield ready for external use!

Want to stay updated or participate? Join my [Discord](https://discord.com/invite/rerCyqAcrw)!

# Current state
- partially reverse-engineered "LUCKY Fish Finder"
- get raw data from echo receiver/amplifier to FastLOGIC/Arduino
- plot data in a waterfall chart using Matplotlib + Python
- DIY transducer built and tested (works)
- TUSS4470 board built and tested (works)
- TUSS4470 Arduino code example done
- TUSS4470 hardware changed to support transformers to drive higher voltage piezos (like 200kHz for underwater)
- underwater tests successful! (only tested up to 3m range)

The LUCKY fishfinder with a DIY transducer (or stock) RAW amplifier (echo) data can be read using an Arduino, and data can be displayed using Matplotlib + Python. 

The new (January 2025) [TUSS4470 board](TUSS4470_shield_001/) is now able to use transducers (40kHz and 200kHz tested), drive them, receive echos, filter the signal and send the RAW echo data to the (same) Python backend. For good results, use a high input voltage like 25V DC on the XT30 connector.
  
  
The [LUCKY fishfinder hack](reverse_engineering/) is pretty much obsolte and replaced by the TUSS4470 board. If you want to play with custom sonar, use this!

--------
# TUSS4470 Ultrasonic Transducer Driver Arduino Board
This [PCB-board](TUSS4470_shield_001/TUSS4470_shield_hardware) is an Arduino (Uno) compatible board to test the Texas Instruments TUSS4470 Ultrasonic driver IC. The provided example [Arduino UNO code](TUSS4470_shield_001/TUSS4470_arduino/TUSS4470_shield.ino) lets you drive a 40kHz transducer, apply noise filtering, and send the echo via Serial to the [Python backend](TUSS4470_shield_001/live_waterfall_python/live_waterfall.py). You can change the code to your needs (i.e. to use other frequencies, sample sizes, speed etc.). The Arduino UNO clock speed and RAM size limit the sampling speed to a resolution of ca. 1-2cm in air and 4cm (ca. 13uS/sample) under water and to ca. 850 Samples. An Arduino MEGA should solve this issue partially.

TUSS4470 Arduino Shield:
<img alt="PCB overview TUSS4470" src="/TUSS4470_shield_002/TUSS4470_shield_hardware/images/top.jpg">

<img alt="PCB overview TUSS4470" src="/TUSS4470_shield_002/TUSS4470_shield_hardware/images/whole_setup.jpg">




The TUSS4470 works as follows:
After initial setup, a burst of 8 pulses in drive frequency is sent to the TUSS4470 by the Arduino on PIN9. The TUSS4470 sends this pulse to the transducer then waits. The Transducer sends this pulse out as a short pulse of sound. Echos reflected by obstacles bounce back to the transducer and excite a voltage in it. The TUSS4470 measures that voltage, filters it, amplifies it and sends it to the A0 pin of the Arduino. By reading this amplified voltage, an (or multiple) obstacles can be detected. The Python script plots this data in a waterfall diagram.

------

DIY transducer assembly with 1:6 transformer and 228kHz transducer for water:
<img alt="PCB overview TUSS4470" src="/documentation/images/transducer_assembly.JPG">

Echogram of a test with DIY transducer assembly in the baltic sea, Kiel:
<img alt="PCB overview TUSS4470" src="/documentation/images/baltic_test200khz.jpg">

Echogram in saltwater vertical and second half horizontal pointing to an underwater ladder(8x speed):
<img alt="PCB overview TUSS4470" src="/documentation/images/echogram_animation.gif">

# Videos
[![LINK TO VIDEO 1](https://img.youtube.com/vi/eJ8jVEQSx_Y/0.jpg)](https://www.youtube.com/watch?v=eJ8jVEQSx_Y)

[![LINK TO VIDEO 2](https://img.youtube.com/vi/Bxh3rWd5RZk/0.jpg)](https://www.youtube.com/watch?v=Bxh3rWd5RZk)

[![LINK TO VIDEO 3](https://img.youtube.com/vi/UDYWQIizN7A/0.jpg)](https://www.youtube.com/watch?v=UDYWQIizN7A)

# Useful Links
https://www.rapp-instruments.de/RemoteSensing/Roves/sidescan/sidescan.htm 

https://www.youtube.com/watch?v=ZtUkt8Q4EJE

# Shopping list
 Transducers: 
 
 https://de.aliexpress.com/item/1005006007865920.html
 
 https://de.aliexpress.com/item/1005007032482539.html
 
 https://de.aliexpress.com/item/1005006299774405.html
 
 https://de.aliexpress.com/item/4000389134890.html
 
 https://de.aliexpress.com/item/1005006546490802.html

 Transformers to step up transducer voltage:
 
 https://de.aliexpress.com/item/1005003733606845.html

 Matching capacitors:
 
 https://de.aliexpress.com/item/1005007159862392.html
 
 Lucky Fishfinder: 
 
 https://de.aliexpress.com/item/32711659077.html


 # Big thanks for your support!
 www.kogger.tech


