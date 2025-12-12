---
layout: default
title: Desktop Interface
parent: Getting Started
nav_order: 3
---

# Getting Started Open Echo Interface Software

The ***Open Echo Interface*** is a cross-platform Python application that interacts with the Arduino + TUSS4470 Shield. 
It displays ultrasonic echo data in real-time using a waterfall chart visualization. 
The application is intended primarily as a testing and development tool, but is stable enough for continuous use -tested for several days on a Raspberry Pi 4 without issues.

### Key Features
- Connects to Open Echo hardware over serial or UDP
- Displays real-time and historical data in a waterfall chart
- Auto-gain to adjust the waterfall chart colors
- Shows detected depth, and (if supported) temperature and drive voltage (`vDRV`)

> **Note**  
> This interface is primarily intended for development and testing. It's proven stable, but not yet a polished end-user application.

---

## Installation & Setup

### 1. Install openecho
```bash
pip install open-echo
```

### 2. Start Open Echo Interface Software
Run the following command to start the web server. 
```bash
openecho desktop
```

Select the correct COM port, then click Connect or press c on your keyboard. Once connected, the Open Echo board will begin streaming data, which will appear on the right side of the interface.
The red horizontal line indicates the currently detected depth, based on the strongest first echo received after the ring-down delay.

<img alt="Open Echo Interface Software" src="/documentation/images/echo_software_screenshot.jpg">


### 4. Change to your own needs

You can change different settings in the first lines of the [**Open Echo Interface**](https://github.com/neumi/open_echo/tree/main/python/src/open_echo/desktop.py) code to customize it to your specific use cases.

### 📊 Parameter Settings

| Parameter         | Description |
|------------------|-------------|
| `BAUD_RATE`       | Must match the baud rate configured in the Arduino firmware. |
| `NUM_SAMPLES`     | Must match the `NUM_SAMPLES` value used in the Arduino firmware. Can be overriden in the interface settings |
| `MAX_ROWS`        | Sets the number of historical measurements displayed in the chart before it scrolls. |
| `Y_LABEL_DISTANCE`| Defines the vertical axis label spacing, in centimeters. |
| `SPEED_OF_SOUND`  | Used to convert sample timing into distance. Set to ~330 for air, ~1450 for water. Can be overriden in the interface settings|
| `SAMPLE_TIME`     | Sampling interval in microseconds. For the Arduino UNO with [TUSS4470_arduino.ino](arduino/TUSS4470_arduino/TUSS4470_arduino.ino), this must be set to **13.2 µs**. Can be overriden in the interface settings|


--- 
Want to stay updated, have questions or want to participate? Join my [Discord](https://discord.com/invite/rerCyqAcrw)!

Or write an issue. Thanks!
