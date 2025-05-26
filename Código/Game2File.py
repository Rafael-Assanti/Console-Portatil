"""
@file Game2File.py
@brief Fixed Space Invaders game with proper type conversion
"""

from machine import Pin, I2C, PWM
from ssd1306 import SSD1306_I2C
from upy_adafruit_mpu6050 import MPU6050
import utime
import random

class SpaceInvadersGame:
    def __init__(self, i2c, shoot_button_pin=10, exit_button_pin=11):
        """Initialize the game with hardware connections"""
        self.oled = SSD1306_I2C(128, 64, i2c)
        self.mpu = MPU6050(i2c)
        self.shoot_button = Pin(shoot_button_pin, Pin.IN, Pin.PULL_UP)
        self.exit_button = Pin(exit_button_pin, Pin.IN, Pin.PULL_UP)
        self.buzzer = PWM(Pin(22))
        
        # Game settings
        self.PLAYER_WIDTH = 8
        self.PLAYER_HEIGHT = 6
        self.ENEMY_WIDTH = 8
        self.ENEMY_HEIGHT = 6
        self.BULLET_WIDTH = 2
        self.BULLET_HEIGHT = 4
        self.ENEMY_ROWS = 3
        self.ENEMY_COLS = 5
        
        # Game state
        self.reset_game()
        self.filtered_tilt = 0.0
        self.alpha = 0.2  # For accelerometer filtering

    def reset_game(self):
        """Reset all game variables to initial state"""
        self.player_x = 64 - self.PLAYER_WIDTH // 2
        self.player_y = 56
        self.bullets = []
        self.enemies = []
        self.score = 0
        self.s = 1
        self.game_active = True
        self.last_shot = 0
        self.enemy_direction = 1
        self.enemy_move_interval = 500  # ms
        self.last_enemy_move = utime.ticks_ms()
        
        # Create enemy grid
        for row in range(self.ENEMY_ROWS):
            for col in range(self.ENEMY_COLS):
                self.enemies.append({
                    'x': 20 + col * 20,
                    'y': 10 + row * 10,
                    'active': True
                })

    def draw_player(self):
        """Draw the player's ship"""
        self.oled.fill_rect(int(self.player_x), int(self.player_y), 
                           self.PLAYER_WIDTH, self.PLAYER_HEIGHT, 1)
        # Draw ship point
        self.oled.fill_rect(int(self.player_x) + 3, int(self.player_y) - 2, 2, 2, 1)

    def draw_bullets(self):
        """Draw all active bullets"""
        for bullet in self.bullets:
            self.oled.fill_rect(int(bullet['x']), int(bullet['y']), 
                               self.BULLET_WIDTH, self.BULLET_HEIGHT, 1)

    def draw_enemies(self):
        """Draw all active enemies"""
        for enemy in self.enemies:
            if enemy['active']:
                self.oled.fill_rect(int(enemy['x']), int(enemy['y']), 
                                   self.ENEMY_WIDTH, self.ENEMY_HEIGHT, 1)
                # Draw enemy eyes
                self.oled.fill_rect(int(enemy['x']) + 2, int(enemy['y']) + 1, 2, 2, 0)
                self.oled.fill_rect(int(enemy['x']) + 5, int(enemy['y']) + 1, 2, 2, 0)

    def update_player(self):
        """Update player position based on tilt"""
        accel_x = float(self.mpu.acceleration[1])
        self.filtered_tilt = self.alpha * accel_x + (1 - self.alpha) * self.filtered_tilt
        
        # Update player position
        self.player_x += self.filtered_tilt * 1.5
        self.player_x = max(0, min(128 - self.PLAYER_WIDTH, self.player_x))

    def update_bullets(self):
        """Move all bullets and check for hits"""
        bullets_to_keep = []
        
        for bullet in self.bullets:
            bullet['y'] -= 3  # Move bullet up
            
            # Check if bullet is still on screen
            if bullet['y'] > 0:
                bullets_to_keep.append(bullet)
                
                # Check for enemy hits
                for enemy in self.enemies:
                    if (enemy['active'] and
                        bullet['x'] < enemy['x'] + self.ENEMY_WIDTH and
                        bullet['x'] + self.BULLET_WIDTH > enemy['x'] and
                        bullet['y'] < enemy['y'] + self.ENEMY_HEIGHT and
                        bullet['y'] + self.BULLET_HEIGHT > enemy['y']):
                        
                        enemy['active'] = False
                        self.score += 10
                        self.play_hit_sound()
                        if bullet in bullets_to_keep:
                            bullets_to_keep.remove(bullet)
                        break
        
        self.bullets = bullets_to_keep

    def update_enemies(self):
        """Move enemies and check for game over"""
        current_time = utime.ticks_ms()
        if utime.ticks_diff(current_time, self.last_enemy_move) > self.enemy_move_interval:
            self.last_enemy_move = current_time
            
            # Check if enemies need to change direction
            change_direction = False
            for enemy in self.enemies:
                if enemy['active']:
                    if (enemy['x'] <= 2 and self.enemy_direction < 0) or \
                       (enemy['x'] >= 128 - self.ENEMY_WIDTH - 2 and self.enemy_direction > 0):
                        change_direction = True
                        break
            
            if change_direction:
                self.enemy_direction *= -1
                # Move enemies down
                for enemy in self.enemies:
                    if enemy['active']:
                        enemy['y'] += 5
            else:
                # Move enemies sideways
                for enemy in self.enemies:
                    if enemy['active']:
                        enemy['x'] += 2 * self.enemy_direction
            
            # Increase speed as enemies are destroyed
            active_enemies = sum(1 for e in self.enemies if e['active'])
            if active_enemies > 0:
                self.enemy_move_interval = max(200, 1000 - (len(self.enemies) - active_enemies) * 50)
        
        active_enemies = sum(1 for e in self.enemies if e['active'])
        if active_enemies == 0:
            self.respawn_enemies()
        # Check if enemies reached bottom
        for enemy in self.enemies:
            if enemy['active'] and enemy['y'] >= self.player_y - 5:
                self.game_over()
                return

    def respawn_enemies(self):
    """Reset enemies for a new wave"""
    self.enemies = []
    # Spawn enemies slightly lower each wave for difficulty
    for row in range(self.ENEMY_ROWS):
        for col in range(self.ENEMY_COLS):
            self.enemies.append({
                'x': 20 + col * 20,
                'y': 10 + row * 12,  # Increased Y for difficulty
                'active': True
            })
    # Increase game speed slightly
    self.enemy_move_interval = max(200, self.enemy_move_interval - 50)
    
    def shoot(self):
        """Create a new bullet from player position"""
        current_time = utime.ticks_ms()
        if utime.ticks_diff(current_time, self.last_shot) > 500:  # Shooting cooldown
            self.bullets.append({
                'x': self.player_x + self.PLAYER_WIDTH // 2 - 1,
                'y': self.player_y - self.BULLET_HEIGHT
            })
            self.last_shot = current_time
            self.play_shoot_sound()

    def play_shoot_sound(self):
        """Play shooting sound effect"""
        self.buzzer.freq(800)
        self.buzzer.duty_u16(3000)
        utime.sleep_ms(50)
        self.buzzer.duty_u16(0)

    def play_hit_sound(self):
        """Play enemy hit sound effect"""
        self.buzzer.freq(2000)
        self.buzzer.duty_u16(5000)
        utime.sleep_ms(100)
        self.buzzer.duty_u16(0)

    def game_over(self):
        """Handle game over sequence"""
        self.game_active = False
        self.oled.fill(0)
        self.oled.text("GAME OVER", 30, 20, 1)
        self.oled.text(f"Score: {self.score}", 40, 35, 1)
        self.oled.text("Press Button", 20, 50, 1)
        self.oled.show()
        
        # Play game over sound
        for freq in [400, 300, 200]:
            self.buzzer.freq(freq)
            self.buzzer.duty_u16(6000)
            utime.sleep_ms(150)
        self.buzzer.duty_u16(0)
        
        # Wait for button press
        while self.shoot_button.value():
            utime.sleep_ms(50)

    def update(self):
        """Main game update function"""
        if not self.game_active:
            return False
        
        # Check for exit first
        if not self.exit_button.value():
            while not self.exit_button.value():  # Wait for release
                utime.sleep_ms(10)
            return False
        
        self.oled.fill(0)
        
        # Update game elements
        self.update_player()
        self.update_bullets()
        self.update_enemies()
        
        # Check for shooting
        if not self.shoot_button.value():
            self.shoot()
            while not self.shoot_button.value():  # Wait for release
                utime.sleep_ms(10)
        
        # Draw everything
        self.draw_enemies()
        self.draw_player()
        self.draw_bullets()
        
        # Draw score and lives
        self.oled.text(f"Score: {self.score}", 0, 0, 1)
        
        self.oled.show()
        return True