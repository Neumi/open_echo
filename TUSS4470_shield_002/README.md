# Open Echo TUSS4470 Shield Getting Started Guide

The TUSS4470 is an ultrasonic driver and receiver IC designed for seamless interaction with ultrasonic transducers. The TUSS4470 Arduino Shield is a development board that enables quick evaluation of the TUSS4470's features using the Arduino UNO platform.

### Overview
This repository provides a quick-start guide and example Arduino sketches for experimenting with Time-of-Flight (ToF) applications using the TUSS4470. The shield is ideal for development, testing, and prototyping, but is not intended as a finished consumer product.

### Getting Started
Connect the shield to an Arduino UNO.

Upload one of the provided example sketches to explore different features of the TUSS4470.

Use the Python software to see the echoes.

### Ordering
The shield can be easily ordered via [JLCPCB](https://jlcpcb.com/?from=Neumi) or other PCB fabrication services.

> [!Note]
> I still have a few boards available, feel free to DM me on [Discord](https://discord.com/invite/rerCyqAcrw) if you're interested.

<img alt="PCB overview TUSS4470" src="/documentation/images/shield_pinout.png">


## Electrical Connections
The TUSS4470 Shield is designed specifically for use with the Arduino UNO. It is not software- or pin-compatible with other Arduino boards at this time.

### Pin Connections
The shield interfaces with the Arduino UNO the following:
- SPI interface
- Four digital GPIOs
- Analog pin A0

### Capacitor Selection for Transducer Frequency
To support different ultrasonic transducers and their respective drive frequencies, the board provides preset capacitor options for:
- 40 kHz
- 150 kHz
- 200 kHz

Use the onboard jumpers to select the appropriate cINN and cFLT values:

For 150 kHz, select the "custom" jumper for cINN and the "200kHz" jumper for cFLT.

Refer to the silkscreen or schematic for jumper positions.
If you want to drive other frequencies, desolder the "CUSTOM" capacitors and solder your own, calculated values. 

These are some example values for other frequencies:
| cFLT nF     | cINN nF     | Frequency kHz  |
|-------------|-------------|----------------|
| 15,91550775 |  106,103385 |            40  |
| 6,366203101 | 42,44135401 |           100  |
| 4,244135401 |   28,294236 |           150  |
|  3,18310155 |   21,220677 |           200  |
| 2,792194343 | 18,61462895 |           228  |
|   2,1220677 |   14,147118 |           300  |
| 1,591550775 |  10,6103385 |           400  |
| 1,399165517 | 9,327770111 |           455  |
|  1,27324062 | 8,488270801 |           500  |
|  1,06103385 | 7,073559001 |           600  |

### Power Supply Options
The board supports two power input options:
- VIN (Arduino VIN pin):
Use this when the transducer operates at 12V max, as the Arduino cannot tolerate higher voltages.

- XT30 Connector:
Use this if you require higher voltage (up to 28V max) for more powerful transducers.

Ensure proper polarity and voltage limits when using this input.

> [!Warning]
> Do not exceed 28V input. Higher voltages can damage the board or components. Ensure proper polarity!

### Transducer Connection
Connect your PZT crystal or preassembled ultrasonic transducer to the "Transducer" header:

- Top pin: Ground (GND) / Shield
- Bottom pin: Signal

> [!Important]
> Proper polarity is crucial to minimize electrical noise and ensure optimal performance.

