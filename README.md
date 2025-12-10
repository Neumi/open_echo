<img alt="Open Echo Cover" src="documentation/images/open_echo_logo.svg">

## Universal Open-Source SONAR Controller and Development Stack

An ongoing open-source hardware and software project for building sonar systems for testing, boating, bathymetry, and research.  
The most commonly used hardware is the [TUSS4470 Arduino Shield](TUSS4470_shield_002/), which stacks on top of an Arduino Uno to drive the TUSS4470 ultrasonic driver.  
The board can run the [RAW Data Firmware](TUSS4470_shield_002/getting_started_TUSS4470_firmware.md) to operate a wide variety of ultrasonic transducers, covering frequencies from 40 kHz up to 1000 kHz in different media such as air or water.  

The [NMEA Output Firmware](TUSS4470_shield_002/arduino/NMEA_DBT_OUT/NMEA_DBT_OUT.ino) can read depth data from commercially available in-water ultrasonic transducers (e.g., on boats) and output NMEA0183-compatible data to a computer or a UART-connected device such as a Pixhawk or other controllers.  

Open Echo has been tested on multiple ultrasonic transducers and is compatible with all of them—from car parking sensors to Lowrance Tripleshot side-scan transducers.  

The [Python Interface Software](TUSS4470_shield_002/getting_started_interface.md) connects to Open Echo boards running the [RAW Data Firmware](TUSS4470_shield_002/getting_started_TUSS4470_firmware.md). It can display raw echo data, change configurations, output a TCP depth data stream, and more.  

Check the [Getting Started Guide](TUSS4470_shield_002/README.md)!  

If something is unclear or you find a bug, please open an issue.  


Raw Data Waterfall chart in the Python Desktop software:  
<img alt="Open Echo Interface Software" src="/documentation/images/echo_software_screenshot.jpg">


## Getting the Hardware

If you need the hardware, you can order it using the [Hardware Files](TUSS4470_shield_002/TUSS4470_shield_hardware/TUSS4470_shield) from a board + SMT house ([JLC recommended](https://jlcpcb.com/?from=Neumi)).

They can also be bought as a complete and tested set direclty from Elecrow: https://www.elecrow.com/open-echo-tuss4470-development-shield.html

All profits go directly toward supporting and advancing the Open Echo project!

<b>If you don't order the boards directly from me or Elecrow, please be aware that I can't provide support.</b>

[TUSS4470 Arduino Shield](TUSS4470_shield_002/):  
<img alt="PCB overview TUSS4470" src="/TUSS4470_shield_002/TUSS4470_shield_hardware/images/top.jpg">

### This project is currently in development. The [TUSS4470 Development Shield](TUSS4470_shield_002/) is ready for external use!  
Development is ongoing—check the documentation and Discord channel for the latest updates.  

Want to stay updated or participate? Join the [Discord](https://discord.com/invite/rerCyqAcrw)!  

Check the [Getting Started Guide](TUSS4470_shield_002/README.md).  

## Vision
An accessible Open Source SONAR stack for development, research and real use:
- Open Source SONAR technology for differernt use cases
- support for a variety of commercial or DIY transducers in water and air
- relatively simple hardware that can be ordered from a board house
- easy entry for less experienced users
- community for exchange and development
- development of more advanced SONAR applications

--------
## Current State
- Universal TUSS4470-based Arduino shield for testing ultrasonic transducers  
- Python interface software for raw data visualization, configuration, and TCP data output  
- Tested depth range of at least 50 m in water  
- NMEA0183 compatible (DBT data output to other devices)  
- New all-in-one boards with STM32, TUSS4470, and boost converter currently in development
- picoW implementation in development (already successfull)
- UDP network RAW data transfer from picoW to Python interface running

--------
## Progress

The new (May 2025) [TUSS4470 Arduino Shield](TUSS4470_shield_002/) supports transducers from 40 kHz to 1000 kHz. It can drive them, receive echoes, filter signals, and send raw echo data to the Python backend.  
Driver voltage can be supplied from Arduino VIN or via the external XT30 connector. With an MT3608 boost converter, USB can be used as a power supply and boosted to the desired drive voltage (manual soldering required).  

The [TUSS4470 Arduino Shield](TUSS4470_shield_002/) is and will remain the main development board for this project. It is an excellent platform for testing and development.  
It can drive a wide range of transducers at different voltages, but it is limited by RAM size and sampling speed. You can capture 1800 samples at 12 microseconds per sample (~18 m range in water) with 8-bit resolution. For longer ranges, you can add a delay to capture echoes from more distant objects.  
This makes it a perfect board for learning, testing, and prototyping. Most software development is done using this board.  

For special use cases, additional boards and software are under development. 
Check the [development](development) folder for development work.

--------
## Open Echo Interface Software

Firmware examples are available in each project folder.  
The [**Open Echo Interface Software**](TUSS4470_shield_002/echo_interface.py) allows you to control Open Echo boards, view live data, and adjust board settings.  

Live echogram in water on Python software (6x speed):  
<img alt="Software running with live echo data" src="documentation/images/echogram_fast.gif">

## Test results Baltic Sea
Tested using a built-in 150 kHz SEAFARER transducer, powered at 15-20 V via an MT3608 boost converter from USB. In the plots, data capture begins at the bottom.

<table>
  <tr>
    <td align="center">
      <img src="documentation/images/baltic_sea_tests/38m_range.png" alt="38m Range" width="300"/><br/>
      <sub><b>38 m range test</b></sub>
    </td>
    <td align="center">
      <img src="documentation/images/baltic_sea_tests/kiel_channel.png" alt="Kiel Channel" width="300"/><br/>
      <sub><b>Kiel Channel sand and mud</b></sub>
    </td>
    <td align="center">
      <img src="documentation/images/baltic_sea_tests/stollergrund.png" alt="Stollergrund" width="300"/><br/>
      <sub><b>Slope near Stollergrund</b></sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="documentation/images/baltic_sea_tests/stones_sand.png" alt="Stones and Sand" width="300"/><br/>
      <sub><b>Stones and sandy seabed</b></sub>
    </td>
    <td align="center">
      <img src="documentation/images/baltic_sea_tests/fish.png" alt="Fish" width="300"/><br/>
      <sub><b>Fish detection</b></sub>
    </td>
    <td align="center">
      <img src="documentation/images/baltic_sea_tests/multi_reflections_seaweed.png" alt="Multiple Reflections" width="300"/><br/>
      <sub><b>Multiple reflections and seaweed</b></sub>
    </td>
  </tr>
  
</table>

## Videos

[![LINK TO LATEST VIDEO](https://img.youtube.com/vi/XF7rNGt6UYA/maxresdefault.jpg)](https://www.youtube.com/watch?v=XF7rNGt6UYA)

https://www.youtube.com/watch?v=R3_NO2F7PsI  
https://www.youtube.com/watch?v=msbLVsY8xhQ  
https://www.youtube.com/watch?v=eJ8jVEQSx_Y  
https://www.youtube.com/watch?v=Bxh3rWd5RZk  
https://www.youtube.com/watch?v=UDYWQIizN7A  

## Useful Links
https://www.rapp-instruments.de/RemoteSensing/Roves/sidescan/sidescan.htm  
https://www.youtube.com/watch?v=ZtUkt8Q4EJE  

## Transducers: 

| Transducer Name | Ranking | Description                                                             | Frequency | Range Air/Water |  Price | Link |
|-----------------|---------|-------------------------------------------------------------------------|-----------|-----------------|--------|------|
| NASA / Seafarer 150kHz Echo Sounder | ⭐ ⭐ ⭐ | NASA in-hull boat transducer for echo sounding and simple fish-finding | 150kHz | >2m/>50m | 50-100€ | https://www.nasamarine.com/product/depth-transducer-with-7-metre-cable/7 
| Raymarine CPT-S |  ⭐ ⭐ ⭐ | High quality In-hull transducer with two frequencies | 50 + 200kHz | 2m/>50m | 200€ | https://www.raymarine.com/de-de/unsere-produkte/fischfinder-und-sonarmodule/fischfindergeber/cpt-s-durchbruchgeber |
| Lowrance Tripleshot Sidescan | ⭐ ⭐ ⭐ | Sidescan transducer with three FANS + temperature + down-scan | 200 + 455 + 600kHz | 0m/>20m | 200€ | https://www.echolotzentrum.de/shop/lowrance-tripleshot-heckgeber/ |
| Cheap Bathymetry 200kHz | ⭐ ⭐ ⭐ | good range, good price/performance, hard to order | 200kHz | 2m/>30m | 25€ | https://www.alibaba.com/product-detail/Range-customization-lakes-river-surveys-no_1600829423846.html |
| Cheap Car Parking Sensor | ⭐ ⭐ | Great for air, also works in water (not recommended) | 40kHz | >7m/>30m | 5€ | https://de.aliexpress.com/item/1005006546490802.html |
| Water flow sensor transducer | ⭐ ⭐ | Cheap and works in Air and Water. Very narrow beam in Water (about 5°)! | 1000kHz | 0.25m/>10m | 16€ for 5pcs | https://de.aliexpress.com/item/32818381566.html |
| Only for air 200 kHz | ⭐ | has a sinter glass matching layer, can only be used in air | 200kHz | 0.8m/>8m | 10€ | https://de.aliexpress.com/item/1005006007865920.html |
| Different Encapsualated Transducers | ⭐| Can be used for short range testing at higher frequencies | 200-400kHz | ?m/?m | 9-18€ | https://de.aliexpress.com/item/4000389134890.html |
| Very small PZT only | ⭐ | Only for testing / experimentation| 200kHz | 0.2m/?m | 10€ | https://de.aliexpress.com/item/1005007032482539.html |

> [!Note]
> The range values were measured using the TUSS4470 shield and Arduino Uno with an MT3608 boost converter set to 20 V for vDRV, so consider them approximate.

> [!Tip]
> As a general rule of thumb, lower frequencies propagate farther, while higher frequencies produce narrower beams and more detailed echoes.
>
> If you need a transducer for bathymetry, choose one of the first four options. Most commercial marine-grade (boating) transducers are also suitable, as long as they operate in the 40-200 kHz range.


# Big Thanks for Your Support!
www.kogger.tech

## to the awesome project contributors:
Check this Cheap Yellow Display implementation out: https://github.com/matztam/open_echo_cyd_display
  
And all the great stuff JohnCHarrington contributed: https://github.com/JohnCHarrington/open_echo


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Neumi/open_echo&type=date&legend=top-left)](https://www.star-history.com/#Neumi/open_echo&type=date&legend=top-left)
