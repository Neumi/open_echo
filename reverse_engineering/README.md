---
layout: default
title: Lucky Fishfinder
nav_order: 9
---

# open_echo

Reverse engineering of the LUCKY fishfinder to learn about ultrasonics projects from a real product.

Using a trigger and analog pin on an Arduino UNO we can read RAW echo data from the LUCKY fishfinder product.

As of today, there are at least three hardware versions of the LUCKY fishfinder. All of them seem to follow a similar concept, but the pinout is different!

LUCKY fishfinder pins:
<img alt="LUCKY fishfinder pin hack" src="/reverse_engineering/images/fishfinder_pins.JPG">

Measured results using LUCKY fishfinder, FastLOGIC (Arduino) and Matplotlib + Python:
<img alt="LUCKY fishfinder pin hack" src="/reverse_engineering/images/echo_capture.jpg">

The chart shows a measurement of reflection time (translated to cm using 1482m/s speed of sound in water) and the past 50 measurements. The LUCKY fish finder takes around 2.3 full measurements per second. The brigter the pixel, the stronger the return signal. The plot shows the sandy ground in the first 1/4 and the rest is the reflection of a metal ladder in the water (horizontal).


# More info in this video:
[![LINK TO VIDEO](https://img.youtube.com/vi/UDYWQIizN7A/0.jpg)](https://www.youtube.com/watch?v=UDYWQIizN7A)
