import adi
import libm2k
import matplotlib.pyplot as plt
import numpy as np
import colorimeter_functions
import sys

# Configure AD4630 ADC with pyadi-iio
adc_uri = "ip:192.168.10.2"
device_name = "ad4630-16"

adc = adi.ad4630(uri=adc_uri, device_name=device_name)
adc.rx_buffer_size = pow(2, 12)
adc.sample_rate = 10000

adc.rx_enabled_channels= [0, 1]

# Connect to M2K and Initialize Pattern Generator Object
pg_uri = "ip:192.168.2.1"
ctx = libm2k.m2kOpen(pg_uri)
digital = ctx.getDigital()
ps = ctx.getPowerSupply()

# Enable and set power supply pins to +5, -5 V to power up OP Amp
colorimeter_functions.set_powersupply(ps)

# Configure M2K to generate LED driving signals
digital.setSampleRateOut(colorimeter_functions.pg_available_sample_rates[1])

# Enable and configure M2K Digital pins as outputs
# For our add-on board, we need to configure DIO13,DIO14,DIO15
for i in range(13, 16):
    digital.setDirection(i, libm2k.DIO_OUTPUT)
    digital.enableChannel(i, True)
digital.setCyclic(True)

# Create digital buffer, to be pushed to Digital Outputs
# This is used to drive the RGB LED

digital_buffer = colorimeter_functions.create_digital_buffer()
digital.push(digital_buffer)

# Create figure to plot results
fig, (ax1, ax2) = plt.subplots(nrows=2)
fig.set_figheight(6)
fig.set_figwidth(6)

# Set-up FFT Plot
ax1.set_title("FFT Plot")
ax1.set_ylim([0, 500])
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

resp = input("Would you like to run a calibration? \n If so, place clear cuvettes in both "
             "reference and sample. Type y or n , then press Enter. \n")

# Ensure response is typed in correctly
resp = resp.strip()  # This removes all whitespaces
if resp == 'Y':
    resp = 'y'
# Calibration values for Red, Green and Blue
# If you type 'y' these will be calculated based on ADC readings
# Otherwise, they remain 1 and have no effect on the light transmittance
red_cal = 1
green_cal = 1
blue_cal = 1

# Where the magic happens
while True:
    # Get data from AD4630
    data = adc.rx()
    ref_data = np.real(data[0])
    measured_data = np.real(data[2])
    # Compute FFT
    # The compute_fft method defined will return only the positive side of the spectrum
    ref_data_fft = colorimeter_functions.compute_fft(ref_data)
    measured_data_fft = colorimeter_functions.compute_fft(measured_data)

    # Examine FFT plot and enter bin numbers for each color
    # Index of DC is 0
    # Replace 1s with actual bin numbers for each color
    # Hint: to create a list of integer numbers from m to n use range(m, n)
    red_bins = range(204, 207)
    green_bins = range(243, 248)
    blue_bins = range(284, 289)

    # Compute Light transmittance
    red_tr, green_tr, blue_tr = colorimeter_functions.light_transmittance(red_bins, green_bins, blue_bins,
                                                                          measured_data_fft, ref_data_fft)
    # Calibrate transmittance results, so we cannot go over 100%
    if resp == 'y':
        red_cal = 100.0 / red_tr
        green_cal = 100.0 / green_tr
        blue_cal = 100.0 / blue_tr
        print("\n Calibration factors \n")
        print("\n Red :" + str(red_cal) + " \n")
        print("\n Green :" + str(green_cal) + " \n")
        print("\n Blue :" + str(blue_cal) + " \n")

        resp = 'n'
    # Apply calibration 
    red_tr *= red_cal
    blue_tr *= blue_cal
    green_tr *= green_cal

    # We are not interested in decimals here, so we're keeping only the truncated integer number
    # from the computed transmittance values
    transmittance = [np.trunc(red_tr), np.trunc(green_tr), np.trunc(blue_tr)]

    # Plot FFT
    data_ref = 2.0 / len(ref_data_fft) * np.abs(ref_data_fft)
    data_sample = 2.0 / len(measured_data_fft) * np.abs(measured_data_fft)
    line1.set_ydata(data_ref)
    line2.set_ydata(data_sample)

    # Plot Light transmittance
    bars.remove()
    bars = ax2.bar(colors, transmittance, color=bar_colors)
    plt.show(block=False)
    plt.pause(0.5)

    print("Red Light Transmittance ----- {:.2f}".format(red_tr) + "% \n")
    print("Green Light Transmittance ----- {:.2f}".format(green_tr) + "% \n")
    print("Blue Light Transmittance ----- {:.2f}".format(blue_tr) + "% \n")

    # Purple Detector
    # Your Code Here

    # Exit loop and close M2K Context
    if not plt.fignum_exists(1):
        libm2k.contextClose(ctx)
        sys.exit()
