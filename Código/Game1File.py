"""
@file Game1File.py
@brief Bike lane game library with accelerometer controls
"""

from machine import Pin, I2C, PWM
from ssd1306 import SSD1306_I2C
from upy_adafruit_mpu6050 import MPU6050
import utime
import random

class BikeGame:
    def __init__(self, i2c, scl_pin=9, sda_pin=8, buzzer_pin=22, button_pin=10):
        """
        Initialize the game with hardware connections
        """
        self.i2c = i2c
        self.oled = SSD1306_I2C(128, 64, i2c)
        self.mpu = MPU6050(i2c)
        self.buzzer = PWM(Pin(buzzer_pin))
        self.restart_button = Pin(button_pin, Pin.IN, Pin.PULL_UP)
        
        # Game constants
        self.ROAD_LEFT = 24
        self.ROAD_RIGHT = 104
        self.BIKE_WIDTH = 8
        self.CAR_WIDTH = 12
        self.LANE_POSITIONS = [34, 64, 94]  # 3 lanes for cars
        self.MIN_CAR_GAP = 40
        self.GAME_SPEED = 0.8
        self.CRASH_FREQ = 800  # Hz
        self.CRASH_DURATION = 0.2
        
        # Game state
        self.reset_game()
        self.filtered_tilt = 0.0
        self.alpha = 0.2  # For accelerometer filtering

    def reset_game(self):
        """Reset all game variables to initial state"""
        self.bike_x = 64  # Starting position
        self.cars = []
        self.score = 0
        self.game_active = True

    def draw_road(self):
        """Draw the road and lane markings"""
        self.oled.fill_rect(0, 0, 128, 64, 0)
        self.oled.rect(self.ROAD_LEFT, 0, self.ROAD_RIGHT-self.ROAD_LEFT, 64, 1)
        for y in range(0, 64, 8):
            for x in [44, 84]:
                self.oled.pixel(x, y, 1)

    def draw_bike(self):
        """Draw the bike at current position"""
        x = int(self.bike_x - self.BIKE_WIDTH//2)
        self.oled.fill_rect(x, 54, self.BIKE_WIDTH, 8, 1)
        self.oled.fill_rect(x+2, 62, 4, 2, 1)

    def play_crash_sound(self):
        """Play the crash sound effect"""
        for _ in range(2):
            self.buzzer.freq(self.CRASH_FREQ)
            self.buzzer.duty_u16(32768)
            utime.sleep(self.CRASH_DURATION)
            self.buzzer.duty_u16(0)
            utime.sleep(0.1)

    def create_car(self):
        """Create a new car if conditions are right"""
        if self.cars and (64 - self.cars[-1]['y']) < self.MIN_CAR_GAP:
            return
        
        self.cars.append({
            'lane': random.choice([0, 1, 2]),
            'y': -8,
            'x': self.LANE_POSITIONS[random.randint(0, 2)] - self.CAR_WIDTH//2
        })

    def move_cars(self):
        """Move all cars and check for collisions"""
        bike_left = int(self.bike_x - self.BIKE_WIDTH//2)
        bike_right = bike_left + self.BIKE_WIDTH
        
        for car in self.cars:
            car['y'] += self.GAME_SPEED
            self.oled.fill_rect(car['x'], int(car['y']), self.CAR_WIDTH, 8, 1)
            
            car_left = car['x']
            car_right = car_left + self.CAR_WIDTH
            car_bottom = int(car['y']) + 8
            
            if (car_bottom > 54) and (car_left < bike_right) and (car_right > bike_left):
                self.game_over()

        self.cars[:] = [c for c in self.cars if c['y'] < 64]
        self.score += 1

    def game_over(self):
        """Handle game over sequence"""
        self.game_active = False
        self.play_crash_sound()
        self.oled.fill(0)
        self.oled.text("CRASH!", 40, 20, 1)
        self.oled.text(f"Score: {self.score}", 32, 40, 1)
        self.oled.show()
        
        # Wait for button press (active low)
        while self.restart_button.value():
            utime.sleep_ms(50)
        
        self.reset_game()
        self.game_active = True

    def update(self):
        """Update game state - to be called in main loop"""
        if not self.game_active:
            return

        # Accelerometer controls
        accel_x = float(self.mpu.acceleration[1])
        self.filtered_tilt = self.alpha * accel_x + (1 - self.alpha) * self.filtered_tilt
        
        # Update bike position
        self.bike_x += self.filtered_tilt * 0.8
        self.bike_x = int(max(self.ROAD_LEFT + self.BIKE_WIDTH//2, 
                      min(self.ROAD_RIGHT - self.BIKE_WIDTH//2, self.bike_x)))
        
        self.draw_road()
        self.draw_bike()
        
        if random.random() < 0.03:
            self.create_car()
            
        self.move_cars()
        
        self.oled.show()