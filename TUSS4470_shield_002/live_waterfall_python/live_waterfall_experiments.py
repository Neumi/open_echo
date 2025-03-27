import serial
import matplotlib.pyplot as plt
import numpy as np
import time
from matplotlib.widgets import Button, Slider

# Serial port configuration
serial_port = '/dev/tty.usbserial-120'  # Update this with your correct port
baud_rate = 1000000

# Initialize serial connection
ser = serial.Serial(serial_port, baud_rate)

# Parameters for the waterfall chart
num_samples = 1600  # Number of samples per measurement sequence
max_cols = 150  # Number of columns to display in the waterfall chart

# Data storage
data = np.zeros((num_samples, max_cols))
times = np.zeros(max_cols)

# Speed of sound in air and sample resolution
speed_of_sound = 330  # meters per second in air
sample_time = 13.2e-6  # 13.2 microseconds in seconds
sample_resolution = (speed_of_sound * sample_time * 100) / 2  # cm

# Set up the plot
plt.ion()
fig, (ax, ax_realtime) = plt.subplots(1, 2, gridspec_kw={'width_ratios': [3, 1]}, figsize=(10, 5))
plt.subplots_adjust(bottom=0.3, right=0.85)

# Waterfall plot
waterfall = ax.imshow(data, aspect='auto', cmap='viridis', interpolation='nearest', vmin=0, vmax=850)
plt.colorbar(waterfall, ax=ax)
ax.invert_yaxis()
ax.set_ylabel('Distance (cm)')

# Adjust y-axis to show only full cm values in 10cm steps
tick_step_cm = 10
y_ticks = np.arange(0, num_samples * sample_resolution, tick_step_cm) / sample_resolution
ax.set_yticks(y_ticks[::-1])
ax.set_yticklabels([f'{dist:.0f}' for dist in y_ticks[::-1] * sample_resolution])

ax.grid(axis='y', linestyle='--', color='gray', linewidth=0.5)
ax.set_xticks(np.linspace(0, max_cols - 1, num=10))
ax.set_xticklabels(['' for _ in range(10)])
ax.set_xlabel('Elapsed Time (s)')

# Real-time signal strength plot
ax_realtime.set_xlim(0, 850)
ax_realtime.set_ylim(0, num_samples)
ax_realtime.set_xlabel('Signal Strength')
ax_realtime.set_title('Real-Time')
sc = ax_realtime.scatter([], [], c=[], cmap='viridis', vmin=0, vmax=850, s=1)
ax_realtime.grid(axis='y', linestyle='--', color='gray', linewidth=0.5)
ax_realtime.set_yticklabels([])  # Remove y-axis labels

# Start time
start_time = time.time()


# Function to parse data from serial input
def parse_data(line):
    try:
        line = line.decode('utf-8').strip()
        if line.startswith("sp"):
            parts = line[2:].split(', ')
            values = [int(x) for x in parts]
            return values
    except Exception as e:
        print(f"Error parsing line: {line} - {e}")
    return None


# Function to send data like Arduino Serial.write() or Serial.print()
def send_uart(value):
    ser.write(value.encode())
    print(f"Sent (raw): {value.encode()}")


# Create buttons
ax_0f = plt.axes([0.1, 0.05, 0.15, 0.075])
ax_0e = plt.axes([0.3, 0.05, 0.15, 0.075])
ax_20 = plt.axes([0.5, 0.05, 0.15, 0.075])
ax_1f = plt.axes([0.7, 0.05, 0.15, 0.075])

btn_0f = Button(ax_0f, 'Send 0x0F')
btn_0e = Button(ax_0e, 'Send 0x0E')
btn_20 = Button(ax_20, 'Send 0x20')
btn_1f = Button(ax_1f, 'Send 0x1F')

btn_0f.on_clicked(lambda event: send_uart("0x0F"))
btn_0e.on_clicked(lambda event: send_uart("0x0C"))
btn_20.on_clicked(lambda event: send_uart("0x20"))
btn_1f.on_clicked(lambda event: send_uart("0x1C"))

# Add sliders
ax_vmax = plt.axes([0.87, 0.3, 0.03, 0.6])  # Vertical slider on the right
vmax_slider = Slider(ax_vmax, 'vmax', 100, 1024, valinit=850, orientation='vertical')

ax_max_cols = plt.axes([0.1, 0.15, 0.65, 0.03])
max_cols_slider = Slider(ax_max_cols, 'max_cols', 50, 300, valinit=max_cols, valstep=10)


def update_vmax(val):
    waterfall.set_clim(vmax=val)
    sc.set_clim(vmin=0, vmax=val)
    fig.canvas.draw_idle()


vmax_slider.on_changed(update_vmax)


def update_max_cols(val):
    global max_cols, data
    max_cols = int(val)
    data = np.zeros((num_samples, max_cols))
    waterfall.set_data(data)
    ax.set_xlim(-0.5, max_cols - 0.5)
    fig.canvas.draw_idle()


max_cols_slider.on_changed(update_max_cols)

# Main loop for receiving and plotting data
while True:
    try:
        line = ser.readline()
        new_data = parse_data(line)

        if new_data and len(new_data) == num_samples:
            elapsed_time = time.time() - start_time
            data = np.roll(data, -1, axis=1)
            data[:, -1] = new_data
            waterfall.set_data(data)

            # Update real-time vertical line chart dynamically
            sc.set_offsets(np.column_stack((new_data, np.arange(num_samples))))
            sc.set_array(np.array(new_data))
            ax_realtime.set_xlim(0, vmax_slider.val)

            ax.set_title(f'Waterfall Chart of Analog Measurements\nSample Resolution: {sample_resolution * 4:.2f} cm')

            fig.canvas.flush_events()
            plt.pause(0.05)

    except KeyboardInterrupt:
        print("Exiting...")
        break

# Close serial connection
ser.close()
