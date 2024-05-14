import random
from machine import Pin
import utime
import uos  # MicroPython os module

# Initialize LED on GPIO Pin 2 for indication
led = Pin(2, Pin.OUT)

# Define current and price constants
CURRENT = 10  # Current in amps
PRICE_PER_UNIT = 35  # Price per unit in currency

# Initialize variables
seconds_counter = 0
price = 0
minute_price_sum = 0
hour_price_sum = 0
previous_days_sum = 0  # Cumulative sum of prices from previous days
days_counter = 1  # Counter for tracking days
minute_counter = 0  # Counter for minutes
hour_counter = 0  # Counter for hours

# Function to calculate price based on power consumption
def calculate_price(power):
    A_power = power / 1000
    Energy = A_power / 3600
    cost = Energy * PRICE_PER_UNIT
    return cost

# Main loop
while True:
    # Generate a random power consumption value between 1500 and 3000 watts
    power = random.randint(1500, 3000)

    # Calculate price
    price = calculate_price(power)

    # Print and store data every second
    with open(f"/data.txt", "a") as data_file:
        led.value(1)
        data_file.write(f"Hour: {hour_counter:02d} - Minute: {minute_counter:02d} - Second: {seconds_counter:02d} - Power: {power} watts - Price: {price:.6f}\n")
        led.value(0)

    # Increment seconds counter
    seconds_counter += 1

    # Sum prices every second for minute file
    minute_price_sum += price

    # Create minute file and write sum of prices every 60 seconds
    if seconds_counter % 15 == 0:
        minute_file_name = f"/{hour_counter:02d}-{minute_counter:02d}_minute.txt"
        with open(minute_file_name, "w") as minute_file:
            minute_file.write(f"Minute {minute_counter:02d} - Price: {minute_price_sum:.6f}\n")
            print(f"Minute {minute_counter:02d} - Price: {minute_price_sum:.6f}")
            # Add minute sum to hourly sum
            hour_price_sum += minute_price_sum
            # Reset minute sum for the next minute
            minute_price_sum = 0
        # Increment minute counter
        minute_counter += 1

    # Check if an hour has passed
    if minute_counter == 15:
        # Create hour file and write sum of prices every 60 minutes (1 hour)
        hour_file_name = f"/{hour_counter:02d}_hour.txt"
        with open(hour_file_name, "w") as hour_file:
            hour_file.write(f"Hour {hour_counter:02d} - Price: {hour_price_sum:.6f}\n")
            print(f"Hour {hour_counter:02d} - Price: {hour_price_sum:.6f}")
            # Reset hourly sum and minute counter for the next hour
            hour_price_sum = 0
            minute_counter = 0

        # Remove previous minute files
        for filename in uos.listdir("/"):
            if filename.endswith("_minute.txt"):
                try:
                    uos.remove(f"/{filename}")
                    print(f"Removed {filename}")
                except OSError as e:
                    print(f"Error removing file {filename}: {e}")

        # Increment hour counter
        hour_counter += 1

        # Check if 24 hours have passed (representing 1 day)
        if hour_counter == 6:
            # Sum all hour prices before writing to the day file
            total_day_price = previous_days_sum
            for filename in uos.listdir("/"):
                if filename.endswith("_hour.txt"):
                    try:
                        with open(f"/{filename}", "r") as hour_file:
                            hour_price = float(hour_file.read().split(":")[1])
                            total_day_price += hour_price
                    except OSError as e:
                        print(f"Error reading hour file: {e}")

            # Create day file and write sum of prices every 24 hours
            day_file_name = f"/day_{days_counter}.txt"
            with open(day_file_name, "w") as day_file:
                day_file.write(f"Day {days_counter} - Price: {total_day_price:.6f}\n")
            # Update previous day sum for next day
            previous_days_sum = total_day_price

            # Reset hour counter and day counter for next day
            hour_counter = 0
            days_counter += 1

    utime.sleep(1)

