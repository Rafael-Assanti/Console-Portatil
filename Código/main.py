"""
@file main.py
@brief Simplified working menu with button control
"""
from Game2File import SpaceInvadersGame
from machine import I2C, Pin, reset
from ssd1306 import SSD1306_I2C
import utime

class MenuSystem:
    def __init__(self, i2c):
        self.i2c = i2c
        self.oled = SSD1306_I2C(128, 64, i2c)
        # Button setup - using your verified working configuration
        self.select_button = Pin(10, Pin.IN, Pin.PULL_UP)
        self.nav_button = Pin(11, Pin.IN, Pin.PULL_UP)
        
        self.options = [
            "1. Moto",
            "2. Aliens",
        ]
        self.selected = 0
        
    def draw_menu(self):
        self.oled.fill(0)
        self.oled.text("Select Game:", 0, 0, 1)
        
        for i, option in enumerate(self.options):
            y_pos = 15 + i * 12
            if i == self.selected:
                self.oled.fill_rect(0, y_pos-2, 128, 12, 1)
                self.oled.text("> " + option, 5, y_pos, 0)
            else:
                self.oled.text("  " + option, 5, y_pos, 1)
    
        self.oled.show()
    
    def run(self):
        while True:
            self.draw_menu()
            
            # Check navigation button (GPIO11)
            if not self.nav_button.value():
                self.selected = (self.selected + 1) % len(self.options)
                while not self.nav_button.value():  # Wait for release
                    utime.sleep_ms(10)
                utime.sleep_ms(200)  # Short delay after navigation
            
            # Check selection button (GPIO10)
            if not self.select_button.value():
                if self.selected == 0:  # Bike Game
                    from Game1File import BikeGame
                    game = BikeGame(self.i2c)
                    while True:
                        game.update()
                        utime.sleep_ms(50)
                        if not self.select_button.value():  # Exit game
                            while not self.select_button.value():
                                utime.sleep_ms(10)
                            break
                elif self.selected == 1:  # Space Invaders
                    game = SpaceInvadersGame(self.i2c, 10, 11)  # shoot=10, exit=11
                    while game.update():  # Will return False when game ends or exit pressed
                        utime.sleep_ms(50)
                    
                elif self.selected == 3:  # Turn Off
                    self.oled.fill(0)
                    self.oled.text("Goodbye!", 40, 30, 1)
                    self.oled.show()
                    utime.sleep(2)
                    reset()
                
                while not self.select_button.value():  # Wait for release
                    utime.sleep_ms(10)
                utime.sleep_ms(200)  # Short delay after selection
            
            utime.sleep_ms(50)  # Main loop delay

# Initialize hardware
i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=400000)
menu = MenuSystem(i2c)
menu.run()