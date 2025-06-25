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
| cFLT nF | cINN nF | Frequency kHz  |
|---------|---------|----------------|
|  15,91  |  106,10 |            40  |
|  6,36   |  42,44  |           100  |
|  4,24   |  28,29  |           150  |
|  3,18   |  21,22  |           200  |
|  2,79   |  18,61  |           228  |
|  2,12   |  14,14  |           300  |
|  1,59   |  10,61  |           400  |
|  1,39   |  9,32   |           455  |
|  1,27   |  8,48   |           500  |
|  1,06   |  7,07   |           600  |

### Power Supply Options
The board supports two power input options:
- VIN (Arduino VIN pin):
Use this when the transducer operates at 12V max, as the Arduino cannot tolerate higher voltages.

- XT30 Connector:
Use this if you require higher voltage (up to 28V max) for more powerful transducers.

> [!Tip]
> To get started, use a 12V power supply. Many ultrasonic transducers operate reliably at this voltage.
> Lower voltages may not adequately excite the transducer, resulting in weak or no echo signals.

> [!Warning]
> Do not exceed 28V input. Higher voltages can damage the board or components. Ensure proper polarity!

### Transducer Connection
Connect your PZT crystal or preassembled ultrasonic transducer to the "Transducer" header:

- Top pin: Ground (GND) / Shield
- Bottom pin: Signal

> [!Important]
> Proper polarity is crucial to minimize electrical noise and ensure optimal performance.

