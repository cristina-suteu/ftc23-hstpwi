import libm2k
import numpy as np
import matplotlib.pyplot as plt
import colorimeter_functions
import sys

uri = "ip:192.168.2.1"

# Connect to M2K and Initialize ADC and Pattern Generator Objects
ctx = libm2k.m2kOpen(uri)
ctx.calibrateADC()
adc = ctx.getAnalogIn()
digital = ctx.getDigital()
ps = ctx.getPowerSupply()

# Enable and set power supply pins to +5, -5 V to power up OP Amp
colorimeter_functions.set_powersupply(ps)

# Configure Analog Inputs

adc.enableChannel(0, True)
adc.enableChannel(1, True)

adc.setSampleRate(colorimeter_functions.pg_available_sample_rates[1])
adc.setRange(0, -1, 1)
adc.setRange(1, -1, 1)

digital.setSampleRateOut(colorimeter_functions.pg_available_sample_rates[1])

# Enable and configure M2K Digital pins as outputs
# For our add-on board, we need to configure DIO13,DIO14,DIO15
for i in range(13, 16):
    digital.setDirection(i, libm2k.DIO_OUTPUT)
    digital.enableChannel(i, True)
digital.setCyclic(True)

# Create digital buffer, to be pushed to Digital Outputs
# this is used to drive the RGB LED

digital_buffer = colorimeter_functions.create_digital_buffer()
digital.push(digital_buffer)

# Create figure to plot results
fig, (ax1, ax2) = plt.subplots(nrows=2)
fig.set_figheight(6)
fig.set_figwidth(6)

# Set-up FFT Plot
ax1.set_title("FFT Plot")
ax1.set_ylim([0, 0.2])

x = np.zeros(2048)
line1, = ax1.plot(x, label="Reference Data")
line2, = ax1.plot(x, label="Sample Data")
ax1.legend()
# Set-up transmittance plot
ax2.set_title("transmittance Plot")
ax2.set_ylim(0, 120)
bar_colors = ['tab:red', 'tab:green', 'tab:blue']
colors = ['red', 'green', 'blue']
transmittance = [0, 0, 0]
bars = ax2.bar(colors, transmittance, color=bar_colors)


red_cal = green_cal = blue_cal = 1.0
if red_cal == green_cal == blue_cal == 1.0: # Cheesy logic - look for a cal file instead. If it doesn't exist, set cal values to unity.
    resp = input("Not calibrated. Would you like to run a calibration? (y or n)\n If so, place clear cuvettes in both reference and sample.")


# Where the magic happens
while True:
    # Get data from M2K
    data = adc.getSamples(pow(2, 12))
    ref_data = data[0]
    measured_data = data[1]

    # Compute FFT
    # The compute_fft method defined will return only the positive side of the spectrum
    ref_data_fft = colorimeter_functions.compute_fft(ref_data)
    measured_data_fft = colorimeter_functions.compute_fft(measured_data)

    # Examine FFT plot and enter bin numbers for each color
    # Index of DC is 0
    # Replace 1s with actual bin numbers for each color
    # Hint: to create a list of integer numbers from m to n use range(m, n)
    red_bins = range(202, 208)
    green_bins = range(243, 249)
    blue_bins = range(284, 290)

    # Compute Light transmittance
    red_tr, green_tr, blue_tr = colorimeter_functions.light_transmittance(red_bins, green_bins, blue_bins,
                                                                          measured_data_fft, ref_data_fft)
        
    if resp == 'y':
        red_cal = 100.0/red_tr
        green_cal = 100.0/green_tr
        blue_cal = 100.0/blue_tr
        resp = 'n'
    # Apply calibration 
    red_tr *= red_cal
    blue_tr *= blue_cal
    green_tr *= green_cal
    
    transmittance = [red_tr, green_tr, blue_tr]

    # Plot FFT
    data_ref = 2.0 / len(ref_data_fft) * np.abs(ref_data_fft)
    data_sample = 2.0 / len(measured_data_fft) * np.abs(measured_data_fft)
    line1.set_ydata(data_ref)
    line2.set_ydata(data_sample)

    # Plot Light transmittance
    bars.remove()
    bars = ax2.bar(colors, transmittance, color=bar_colors)
    plt.show(block=False)
    plt.pause(2)

    print("Red Light Transmittance ----- " + str(red_tr))
    print("Green Light Transmittance ----- " + str(green_tr))
    print("Blue Light Transmittance ----- " + str(blue_tr) + " \n")

    # Purple Detector
    # Your Code Here

    # Exit loop and close M2K Context
    if not plt.fignum_exists(1):
        libm2k.contextClose(ctx)
        sys.exit()
