
# Getting Started with Arduino TUSS4470 Firmware

This repository provides two software components to support the TUSS4470 Arduino Shield:
- [Arduino Firmware](arduino/TUSS4470_arduino/TUSS4470_arduino.ino) - Runs on an Arduino UNO board with the TUSS4470 shield and handles signal generation, echo capture, and communication.
- [Open Echo Interface](echo_interface.py) - A desktop application that communicates with the Arduino, displays echo data as a real-time waterfall chart, and will soon allow runtime configuration of the system.


## Arduino Firmware
The Arduino firmware initializes the TUSS4470 device and manages the ultrasonic signal transmission and echo reception cycle. It sends digitized echo data over the serial interface to a host computer for analysis.

<b/>Key Features</b>
- SPI communication with TUSS4470 chip
- Configurable drive frequency
- Adjustable sampling size (defines detection range)
- Basic bandpass filtering options
- Threshold detection for bottom line detection
- Binary data transfer to Python software

> [!NOTE]
> The firmware is designed to be easily modified. Users are encouraged to experiment with parameters to suit their application needs.

## Uploading the Firmware
1. Open the Arduino IDE.
2. Select your Arduino UNO board and the correct COM port.
4. Load the firmware sketch [TUSS4470_arduino.ino](arduino/TUSS4470_arduino/TUSS4470_arduino.ino).
5. Upload the sketch to the Arduino UNO.


## ⚙️ Configuration Parameters
Below are the key parameters used to control the ultrasonic transducer behavior, echo processing, and filtering. `NUM_SAMPLES` must be kept in sync with the [Open Echo Interface](echo_interface.py). Due to RAM limitations on the Arduino UNO, it can't exceed ~1800 samples.

### 📊 Settings

| Parameter               | Description                                                                                           |
|------------------------|-------------------------------------------------------------------------------------------------------|
| `NUM_SAMPLES`          | Total number of ADC samples per measurement cycle. Must match the sample size used in visualization. Each sample is approximately **13.2 µs** long. |
| `BLINDZONE_SAMPLE_END` | Number of initial samples to ignore after sending the ultrasonic pulse. Avoids transducer ringdown echoes. |
| `THRESHOLD_VALUE`      | Echo amplitude threshold for detecting the bottom. First echo stronger than this (after blind zone) is used. |

```cpp
#define NUM_SAMPLES 1800         // One frame of data at full sampling speed (~24 ms) -> in water ~18m -> in air ~4m
#define BLINDZONE_SAMPLE_END 200 // Ignore first 200 samples during early transducer ringdown
#define THRESHOLD_VALUE 0x19     // Echo strength threshold for bottom or obstacle detection
```

### 📡 Transducer Drive Frequency

The ultrasonic burst frequency is set by configuring **DRIVE_FREQUENCY**.
Enter the resonant frequency in Hz of your transducer. The TUSS4470 supports drive frequencies between 40 and 1000 kHz.

**Example Configuration:**
For **40 kHz**:  
```cpp
#define DRIVE_FREQUENCY 40000
```

#### 🔧 Alternative Frequencies

| Frequency | Notes                                     |
|-----------|-------------------------------------------|
| 40 kHz    | Car parking sensor                        |
| 50 kHz    | Raymarine CPT-S secondary frequency       |
| 100 kHz   | Chrhartz DIY transducer                   |
| 151 kHz   | Muebau transducer                         |
| 200 kHz   | Raymarine CPT-S                           |
| 216 kHz   | Mini transducer                           |
| 230 kHz   | 18mm transducer from AliExpress           |
| 455 kHz   | Lowrance Hook 3TS sidescan                |
| 1000 kHz  | Water flow sensor transducer              |

---

### 🎛️ Band-Pass Filter (TUSS4470)

To reduce noise and isolate the echo signals, a band-pass filter is configured on the **TUSS4470** IC. This should closely match the transducer’s drive frequency and the cFLT and cINN values on the board, see [Getting Started Guide](README.md#custom-capacitor-configuration).

**Example Configuration:**

```cpp
#define FILTER_FREQUENCY_REGISTER 0x00 // 40 kHz
```

#### 🧪 Other Filter Register Options

| Filter Register | Frequency | Notes                                  |
|-----------------|-----------|----------------------------------------|
| `0x00`          | 40 kHz    | Car parking sensor                     |
| `0x09`          | 68 kHz    | Secondary frequency [Raymarine CPT-S](https://www.raymarine.com/de-de/unsere-produkte/fischfinder-und-sonarmodule/fischfindergeber/cpt-s-durchbruchgeber)  |
| `0x10`          | 100 kHz   | Chrhartz transducer                        |
| `0x18`          | 151 kHz   | Muebau transducer                      |
| `0x1E`          | 200 kHz   | [Raymarine CPT-S](https://www.raymarine.com/de-de/unsere-produkte/fischfinder-und-sonarmodule/fischfindergeber/cpt-s-durchbruchgeber), [AliExpress 18mm](https://de.aliexpress.com/item/1005006007865920.html), [Alibaba](https://www.alibaba.com/product-detail/Range-customization-lakes-river-surveys-no_1600829423846.html)    |


> 📖 For full configuration details, see the [TUSS4470 Datasheet – Table 7.1](https://www.ti.com/lit/ds/symlink/tuss4470.pdf).

### Summary

To get started, upload the provided Arduino firmware [TUSS4470_arduino.ino](arduino/TUSS4470_arduino/TUSS4470_arduino.ino) to an Arduino UNO using the Arduino IDE. The firmware is preconfigured for a 40 kHz transducer (car parking sensor), which is ideal for first-time setup and testing. Once running, the Arduino continuously sends ultrasonic echo data over USB to the Open Echo Interface Python app for real-time visualization. You can customize parameters such as sample size, blind zone, detection threshold, drive frequency, and filter register to suit other transducers or application ranges. Just make sure NUM_SAMPLES matches in both the Arduino firmware and the Python interface. For most users, starting with the default 40 kHz setup provides the simplest and most reliable baseline.

<b/>Next Steps: Proceed to [Getting Started Open Echo Interface Software](getting_started_interface.md).</b>
