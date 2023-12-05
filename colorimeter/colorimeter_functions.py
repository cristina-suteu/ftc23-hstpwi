import math
import copy
import numpy as np

max_buffer_size = 500000

pg_available_sample_rates = [1000, 10000, 100000, 1000000, 10000000, 100000000]
pg_max_rate = pg_available_sample_rates[-1]  # last sample rate = max rate
pg_channels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

min_nr_of_points = 10

red_freq = 500  # in Hz
green_freq = 600  # in Hz
blue_freq = 700  # in Hz


def get_best_ratio(ratio):
    max_it = max_buffer_size / ratio
    best_ratio = ratio
    best_fract = 1

    for i in range(1, int(max_it)):
        new_ratio = i * ratio
        (new_fract, integral) = math.modf(new_ratio)
        if new_fract < best_fract:
            best_fract = new_fract
            best_ratio = new_ratio
        if new_fract == 0:
            break

    return best_ratio, best_fract


def get_samples_count(rate, freq):
    ratio = rate / freq
    if ratio < min_nr_of_points and rate < pg_max_rate:
        return 0
    if ratio < 2:
        return 0

    ratio, fract = get_best_ratio(ratio)
    # ratio = number of periods in buffer
    # fract = what is left over - error

    size = int(ratio)
    while size & 0x03:
        size = size << 1
    while size < 1024:
        size = size << 1
    return size


def get_optimal_sample_rate_pg(freq):
    for rate in pg_available_sample_rates:
        buf_size = get_samples_count(rate, freq)
    if buf_size:
        return rate


def square_buffer_generator(freq, phase, sample_rate, dutycycle=0.5):
    buffer = []

    nr_of_samples = get_samples_count(sample_rate, freq)
    samples_per_period = sample_rate / freq
    phase_in_samples = ((phase / 360) * samples_per_period)
    scaler = freq / sample_rate
    shift: float = dutycycle / 2
    for i in range(nr_of_samples):
        val = 0 if (((i + phase_in_samples) * scaler + shift) % 1 < dutycycle) else 1
        buffer.append(val)

    return buffer


def square_wave_digital(sig, channel):
    # shifts buffer to the corresponding DIO channel
    dig_buf = list(map(lambda s: int(s) << channel, sig))
    for i in range(8):
        dig_buf.extend(dig_buf)
    return dig_buf


def lcm(x, y, z):
    gcd2 = math.gcd(y, z)
    gcd3 = math.gcd(x, gcd2)

    lcm2 = y * z // gcd2
    lcm3 = x * lcm2 // math.gcd(x, lcm2)
    return int(lcm3)


def extend_buffer(buf, desired_length):
    times = int(desired_length / len(buf))
    aux = copy.deepcopy(buf)

    for i in range(1, times):
        buf.extend(aux)
    return buf


def create_digital_buffer():
    # Create 3 digital clock pattern buffers at 3 different frequencies
    # We will use these to drive the RGB LED
    # Each signal will turn the LED either Red, Blue or Green

    # Do we want to play around with phase, offset and duty cycle ?
    square_dutycycle = 0.5
    square_offset = 0
    square_phase = 0

    sig = square_buffer_generator(red_freq, square_phase, pg_available_sample_rates[1], square_dutycycle)
    red_buf = square_wave_digital(sig, pg_channels[13])

    sig = square_buffer_generator(green_freq, square_phase, pg_available_sample_rates[1], square_dutycycle)
    green_buf = square_wave_digital(sig, pg_channels[14])

    sig = square_buffer_generator(blue_freq, square_phase, pg_available_sample_rates[1], square_dutycycle)
    blue_buf = square_wave_digital(sig, pg_channels[15])

    # Make sure all buffers are the same length
    # Find The Least Common Multiple(LCM) between the lengths of the 3 buffers
    # Extend each buffer until they are the length of LCM

    buffer_length = lcm(len(red_buf), len(green_buf), len(blue_buf))
    red_buf = extend_buffer(red_buf, buffer_length)
    blue_buf = extend_buffer(blue_buf, buffer_length)
    green_buf = extend_buffer(green_buf, buffer_length)

    buffer = []
    if len(red_buf) == len(blue_buf) == len(green_buf):
        for i in range(len(red_buf)):
            bit = red_buf[i] + blue_buf[i] + green_buf[i]
            buffer.append(bit)

    return buffer


def compute_fft(data):
    # Remove DC offset
    data_no_dc = data - np.mean(data)
    # Apply Blackman window
    windowed_signal = data_no_dc * np.blackman(len(data_no_dc))
    data_fft = np.fft.fft(windowed_signal)
    # return only positive half of the spectrum.
    data_fft = data_fft[:len(data_fft) // 2]
    return data_fft # Note that this is still complex data.


def light_transmittance(red_bins, green_bins, blue_bins, measured_data_fft, ref_data_fft):
    # Given the selected bins for Red , Green , Blue --> compute light transmittance
    # Compute Sample_Magnitude and Reference_Magnitude for each color
    red_power_sample = np.sqrt(np.sum(np.abs(measured_data_fft[red_bins]) ** 2.0))
    red_power_ref = np.sqrt(np.sum(np.abs(ref_data_fft[red_bins]) ** 2.0))

    green_power_sample = np.sqrt(np.sum(np.abs(measured_data_fft[green_bins]) ** 2.0))
    green_power_ref = np.sqrt(np.sum(np.abs(ref_data_fft[green_bins]) ** 2.0))

    blue_power_sample = np.sqrt(np.sum(np.abs(measured_data_fft[blue_bins]) ** 2.0))
    blue_power_ref = np.sqrt(np.sum(np.abs(ref_data_fft[blue_bins]) ** 2.0))

    # Calculate Light transmittance : Sample_Magnitude divided by Reference_Magnitude
    red_abs = red_power_sample / red_power_ref * 100
    green_abs = green_power_sample / green_power_ref * 100
    blue_abs = blue_power_sample / blue_power_ref * 100

    return red_abs, green_abs, blue_abs



def set_powersupply(ps):
    # enable and set power supply pins to +5, -5 V to power up OP Amp
    ps.reset()
    ps.enableChannel(0, True)
    ps.pushChannel(0, 5)
    ps.enableChannel(1, True)
    ps.pushChannel(1, -5)
