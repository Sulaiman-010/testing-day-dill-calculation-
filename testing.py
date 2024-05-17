import random
from machine import Pin, SoftI2C, RTC
import utime
import uos  # MicroPython os module

# Initialize SoftI2C for RTC (assumed to be DS3231)
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))  # Update with your pins

# RTC DS3231 address
RTC_ADDR = 0x68

# Function to scan I2C devices
def scan_i2c():
    devices = i2c.scan()
    if devices:
        print('I2C devices found:', [hex(device) for device in devices])
    else:
        print('No I2C devices found')
    return devices

# Function to read time from RTC
def read_rtc_time():
    i2c.writeto(RTC_ADDR, b'\x00')  # Set register pointer to 00h
    data = i2c.readfrom(RTC_ADDR, 7)
    
    def bcd_to_dec(bcd):
        return (bcd // 16) * 10 + (bcd % 16)
    
    second = bcd_to_dec(data[0] & 0x7F)
    minute = bcd_to_dec(data[1] & 0x7F)
    hour = bcd_to_dec(data[2] & 0x3F)
    day = bcd_to_dec(data[4] & 0x3F)
    month = bcd_to_dec(data[5] & 0x1F)
    year = bcd_to_dec(data[6]) + 2000  # Assuming year is stored as offset from 2000
    
    return year, month, day, hour, minute, second

# Function to set the RTC time
def set_rtc_time(year, month, day, hour, minute, second):
    def dec_to_bcd(dec):
        return (dec // 10) * 16 + (dec % 10)
    
    data = bytearray(7)
    data[0] = dec_to_bcd(second)
    data[1] = dec_to_bcd(minute)
    data[2] = dec_to_bcd(hour)
    data[3] = dec_to_bcd(0)  # Day of the week is not used
    data[4] = dec_to_bcd(day)
    data[5] = dec_to_bcd(month)
    data[6] = dec_to_bcd(year - 2000)
    
    i2c.writeto_mem(RTC_ADDR, 0x00, data)

# Check if RTC is initialized by reading its time and checking for default values
def is_rtc_initialized():
    year, month, day, hour, minute, second = read_rtc_time()
    return not (year == 2000 and month == 1 and day == 1 and hour == 0 and minute == 0 and second == 0)

# Initialize LED on GPIO Pin 2 for indication
led = Pin(2, Pin.OUT)

# Define current and price constants
CURRENT = 10  # Current in amps
PRICE_PER_UNIT = 35  # Price per unit in currency

# Initialize variables
price = 0
minute_price_sum = 0
hour_price_sum = 0
previous_days_sum = 0  # Cumulative sum of prices from previous days

# Scan I2C devices
scan_i2c()

# Function to calculate price based on power consumption
def calculate_price(power):
    A_power = power / 1000
    Energy = A_power / 3600
    cost = Energy * PRICE_PER_UNIT
    return cost

# Function to get formatted date string
def get_formatted_date(year, month, day, hour=0, minute=0):
    return f"{day:02d}-{month:02d}-{year} - {hour:02d}h {minute:02d}m"

# Set the RTC time if it hasn't been initialized
if not is_rtc_initialized():
    # Set to current date and time or a specific date and time
    set_rtc_time(2024, 5, 1, 0, 0, 0)

# Main loop
while True:
    # Generate a random power consumption value between 1500 and 3000 watts
    power = random.randint(1500, 3000)

    # Read current time from RTC
    try:
        year, month, day, hour, minute, second = read_rtc_time()
    except OSError as e:
        print(f"Error reading RTC: {e}")
        utime.sleep(1)
        continue

    # Calculate price
    price = calculate_price(power)

    # Print and store data every second
    with open(f"/data.txt", "a") as data_file:
        led.value(1)
        data_file.write(f"{day:02d}-{month:02d}-{year} {hour:02d}:{minute:02d}:{second:02d} - Power: {power} watts - Price: {price:.6f}\n")
        led.value(0)

    # Sum prices every second for minute file
    minute_price_sum += price

    # Create minute file and write sum of prices every 60 seconds
    if second == 59:
        minute_file_name = f"/{get_formatted_date(year, month, day, hour, minute)} - minute.txt"
        with open(minute_file_name, "w") as minute_file:
            minute_file.write(f"{hour:02d}:{minute:02d} - Price: {minute_price_sum:.6f}\n")
            print(f"{hour:02d}:{minute:02d} - Price: {minute_price_sum:.6f}")
            # Add minute sum to hourly sum
            hour_price_sum += minute_price_sum
            # Reset minute sum for the next minute
            minute_price_sum = 0

        # Check if an hour has passed
        if minute == 59:
            # Create hour file and write sum of prices for the hour
            hour_file_name = f"/{get_formatted_date(year, month, day, hour)} - hour.txt"
            with open(hour_file_name, "w") as hour_file:
                hour_file.write(f"{hour:02d}:00 - Price: {hour_price_sum:.6f}\n")
                print(f"{hour:02d}:00 - Price: {hour_price_sum:.6f}")
                # Reset hourly sum for the next hour
                hour_price_sum = 0

            # Print all existing hour files
            print("Existing hour files:")
            for filename in uos.listdir("/"):
                if filename.endswith("-hour.txt"):
                    print(filename)
                    try:
                        with open(f"/{filename}", "r") as hour_file:
                            print(hour_file.read())
                    except OSError as e:
                        print(f"Error reading file {filename}: {e}")

            # Check if a day has passed
            if hour == 23 and minute == 59:
                # Sum all hour prices before writing to the day file
                total_day_price = previous_days_sum
                for filename in uos.listdir("/"):
                    if filename.endswith("-hour.txt"):
                        try:
                            with open(f"/{filename}", "r") as hour_file:
                                for line in hour_file:
                                    hour_price = float(line.split(":")[-1].strip())
                                    total_day_price += hour_price
                        except OSError as e:
                            print(f"Error reading hour file: {e}")

                # Create day file and write sum of prices for the day
                day_file_name = f"/{get_formatted_date(year, month, day)} - day.txt"
                with open(day_file_name, "w") as day_file:
                    day_file.write(f"Day {day:02d}-{month:02d}-{year} - Price: {total_day_price:.6f}\n")
                    print(f"Day {day:02d}-{month:02d}-{year} - Price: {total_day_price:.6f}\n")
                # Update previous day sum for next day
                previous_days_sum = total_day_price

                # Remove previous second, minute, and hour files
                for filename in uos.listdir("/"):
                    if filename.endswith("-minute.txt") or filename.endswith("-hour.txt"):
                        try:
                            uos.remove(f"/{filename}")
                            print(f"Removed {filename}")
                        except OSError as e:
                            print(f"Error removing file {filename}: {e}")

    utime.sleep(1)

