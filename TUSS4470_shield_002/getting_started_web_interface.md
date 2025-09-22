# Getting Started Open Echo Interface Software

The [***Open Echo Web Interface***](echo_interface.py) is a cross-platform Python application that interacts with the Arduino + TUSS4470 Shield. 
It displays ultrasonic echo data in real-time in the browser using a waterfall chart visualization. 
<!-- The application is intended primarily as a testing and development tool, but is stable enough for continuous use -tested for several days on a Raspberry Pi 4 without issues. -->

### Key Features
- Connects to Open Echo hardware over serial
- Displays real-time and historical data in a waterfall chart
<!-- - Auto-gain to adjust the waterfall chart colors -->
- Shows detected depth <!-- and (if supported) temperature and drive voltage (`vDRV`) -->
<!-- - Supports bidirectional communication for debugging and testing -->
- Shows depth at cursor on hover - useful for precise depths of non-ground echoes (fish!)

> **Note**  
> This interface is primarily intended for development and testing. It's proven stable, but not yet a polished end-user application.

---

## Installation & Setup

### 1. Create and activate a virtual environment

```bash
cd open_echo/TUSS4470_shield_002/web
python3 -m venv venv 
source venv/bin/activate 
```

### 2. Install requirements
```bash
pip install -r requirements.txt 
```

### 3. Start Open Echo Interface Software
Run the following command to start the web server. 
```bash
python3 -m uvicorn --host=0.0.0.0 --port=8000 app:app
```
Then go to http://localhost:8000. The first connection will be redirected to /config to set up the connection, then you should see your echoes.


--- 
Want to stay updated, have questions or want to participate? Join my [Discord](https://discord.com/invite/rerCyqAcrw)!

Or write an issue. Thanks!
