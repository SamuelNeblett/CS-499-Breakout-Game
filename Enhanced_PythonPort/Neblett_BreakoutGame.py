# Port and enhancement of 8-2 Assignment: Coding Collisions from SNHU CS-330
# Require GLFW library for OpenGL window and keyboard support
# Install GLFW using: pip install glfw
# Require PyOpenGL to support OpenGL bindings, used for rendering graphics
# Install PyOpenGL using: pip install PyOpenGL
# Require ImGui to support GUI text for OpenGL
# Install ImGui using: pip install imgui-bundle
# NumPy is required for ImGui, install it using: pip install numpy
# Utilized OpenGL for Python reference here:
# https://pythonprogramming.net/opengl-rotating-cube-example-pyopengl-tutorial
# Utilized ImGui for Python and GLFW reference here:
# https://github.com/pthom/imgui_bundle/blob/main/bindings/imgui_bundle/python_backends/examples/example_python_backend_glfw3.py
import imgui_bundle
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
import glfw
from OpenGL.GL import *
import sys
import random
import math
import time
import datetime
import sqlite3

DEG2RAD = 3.14159 / 180

# Gloabal variables for tracking gameplay
# Name for the current player, used for high scores
player_name = "Player"
# Track the current state of the game
# "MENU" = main menu, "PLAYING" = in-game
current_state = "MENU"
# NOTE: score will later be pushed to a database
score = 0
lives = 5
# Flag to track if a new ball can be launched
can_launch = True
current_level = 1
active_bricks = []
world = []

# List of high scores fetched from the database
high_scores = []

# Define brick types
# Added direction-specific reflection bricks for the paddle
class BrickType:
    REFLECTIVE = 0
    DESTRUCTABLE = 1

class OnOff:
    ON = 1
    OFF = 0

# Define the Brick class to represent each brick in the game
class Brick:
    def __init__(self, brick_type, pos_x, pos_y, width, red, green, blue, hits_remaining):
        self.red = red
        self.green = green
        self.blue = blue
        self.x = pos_x
        self.y = pos_y
        self.width = width
        self.brick_type = brick_type
        # If hits_remaining > 1, the brick requires multiple hits to clear
        self.hits_remaining = hits_remaining
        self.onoff = OnOff.ON

    def draw_brick(self):
        if self.onoff == OnOff.ON:
            half_size = self.width / 2

            glColor3d(self.red, self.green, self.blue)
            glBegin(GL_POLYGON)

            glVertex2d(self.x + half_size, self.y + half_size)
            glVertex2d(self.x + half_size, self.y - half_size)
            glVertex2d(self.x - half_size, self.y - half_size)
            glVertex2d(self.x - half_size, self.y + half_size)

            glEnd()

# Define the Paddle class
class Paddle:
    def __init__(self, pos_x, pos_y):
        self.x = pos_x
        self.y = pos_y
        # The paddle size and color will not change, so define those here
        self.width = 0.4
        self.height = 0.1
        self.onoff = OnOff.ON

    def draw_paddle(self):
        glColor3d(1, 0, 0)
        glBegin(GL_POLYGON)

        glVertex2d(self.x + self.width / 2, self.y + self.height / 2)
        glVertex2d(self.x + self.width / 2, self.y - self.height / 2)
        glVertex2d(self.x - self.width / 2, self.y - self.height / 2)
        glVertex2d(self.x - self.width / 2, self.y + self.height / 2)

        glEnd()

class Ball:
    def __init__(self, pos_x, pos_y, radius, velocity_x, velocity_y, red, green, blue):
        self.x = pos_x
        self.y = pos_y
        self.radius = radius
        self.red = red
        self.green = green
        self.blue = blue
        # Replace old direction logic with velocity
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y

        self.onoff = OnOff.ON

    # Check collision with bricks and paddles using AABB
    def check_collision(self, obj):

        # Check if the passed obj is a brick or a paddle
        # The ball can collide with both, both use AABB collision detection
        isbrick = isinstance(obj, Brick)
        ispaddle = isinstance(obj, Paddle)

        # If the ball or brick is off, don't check for collision
        if (self.onoff == OnOff.OFF or obj.onoff == OnOff.OFF):
            return

        # Define a bounding box for the ball for AABB collision detection
        half_width = obj.width / 2
        if isbrick:
            # Bricks are square and have no height component
            half_height = half_width
        elif ispaddle:
            half_height = obj.height / 2

        min_x = obj.x - half_width
        max_x = obj.x + half_width
        min_y = obj.y - half_height
        max_y = obj.y + half_height

        # Find the closest points on X and Y
        # AABB closest point reference adapted from:
        # https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-detection
        closest_x = max(min_x, min(self.x, max_x))
        closest_y = max(min_y, min(self.y, max_y))

        # Find the distance between the ball's center and this closest point
        distance_x = self.x - closest_x
        distance_y = self.y - closest_y

        # Calculate the distance length using the Pythagorean theorem
        # Translated from C++ OpenGL glm::length() from:
        # https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-detection
        distance_length = math.sqrt((distance_x ** 2) + (distance_y ** 2))
        
        # Check if the distance is less than the ball's radius
        # to determine collision events
        if (distance_length < self.radius):
            # Safety check so we don't divide by zero
            if distance_length == 0:
                distance_length = 0.001

            # If the collision is with a brick
            if isbrick:
                self.brick_collision(obj,
                                     distance_length,
                                     distance_x,
                                     distance_y)
            # If the collision is with a paddle
            elif ispaddle:
                 self.paddle_collision(obj,
                                       half_width,
                                       half_height)
    
    # Collision event with a brick
    def brick_collision(self, obj, distance_length, distance_x, distance_y):
        global score

        # Normalize the distance vector to get the collision normal
        # Collision resolution concepts adapted from:
        # https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-resolution
        normal_x = distance_x / distance_length
        normal_y = distance_y / distance_length

        # Reflect the ball's direction based on the collision normal
        # Reflection vector math adapted from:
        # https://math.stackexchange.com/questions/13261/how-to-get-a-reflection-vector
        dot_product = (self.velocity_x * normal_x) + (self.velocity_y * normal_y)

        # Update the ball's velocity based on the reflection formula
        self.velocity_x = self.velocity_x - (2 * dot_product * normal_x)
        self.velocity_y = self.velocity_y - (2 * dot_product * normal_y)

        # Adding direction-based offsets to move the ball slightly
        # above the paddle so it does not get stuck
        # "Sticky paddle" issue referenced here:
        # https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-resolution
        self.x += normal_x * (self.radius - distance_length)
        self.y += normal_y * (self.radius - distance_length)

        # Check the brick type
        # Reflective bricks should change color on collision,
        # but not be destroyed
        if obj.brick_type == BrickType.REFLECTIVE:
            # Increment the color of the brick by 0.1 for each color channel
            obj.red += 0.1
            obj.green += 0.1
            obj.blue += 0.1

            # Wrap each color channel around to 0 once it reaches > 1.0
            if (obj.red > 1.0):
                obj.red = 0.0
            if (obj.green > 1.0):
                obj.green = 0.0
            if (obj.blue > 1.0):
                obj.blue = 0.0
            
        # Destructable bricks should decrement their hit count
        # and be destroyed if hits_remaining <= 0
        elif (obj.brick_type == BrickType.DESTRUCTABLE):
            # Decrement the hits remaining for the destructible brick
            obj.hits_remaining -= 1

            if obj.hits_remaining <= 0:
                obj.onoff = OnOff.OFF
                # Increment score when a destructible brick is destroyed
                score += 100
            else:
                # Decrement the color of the brick by 0.1
                # for each color channel
                obj.red -= 0.1
                obj.green -= 0.1
                obj.blue -= 0.1

                # Wrap each color channel around to 0 once it reaches > 1.0
                if (obj.red < 0.0):
                    obj.red = 1.0
                if (obj.green < 0.0):
                    obj.green = 1.0
                if (obj.blue < 0.0):
                    obj.blue = 1.0
                    
                # Increment score when a destructible brick is hit
                # but not destroyed
                score += 20

    # Collision event with a paddle
    def paddle_collision(self, obj, half_width, half_height):
        # Calculate where the ball hit the paddle on the X axis
        # Used the following as reference for velocity calculation:
        # https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-resolution
        hit_pos_x = (self.x - obj.x) / half_width

        # Additional strength/speed to add to the ball after a hit
        velocity_mod = 0.01
        self.velocity_x = hit_pos_x * velocity_mod

        # Move the ball slightly above the paddle
        # so it does not get stuck
        # "Sticky paddle" issue referenced here:
        # https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-resolution
        self.velocity_y = abs(self.velocity_y)
        self.y = obj.y + half_height + self.radius

    # Called once per frame to handle movement
    def move_one_step(self):
        global lives, can_launch, current_state, player_name, score

        # If the ball is off, don't move the ball
        if self.onoff == OnOff.OFF:
            return

        # Add the new velocity to the X and Y coordinates to move the ball
        self.x += self.velocity_x
        self.y += self.velocity_y

        # Minimum velocity so we don't divide by zero
        # and so the ball never moves too slowly
        min_velocity = 0.005

        # Friction modifier to slow down as it hits things
        friction_mod = 0.3

        # Left bounds collisions
        if (self.x < -1 + self.radius):
            self.x = -1 + self.radius

            # Bounce off of the wall and slow down the ball
            self.velocity_x = (self.velocity_x * -1) * friction_mod
            
            # Ensure the velocity never goes below 0, so it always moves
            if abs(self.velocity_x) < min_velocity:
                self.velocity_x = min_velocity

        # Right bounds collisions
        if (self.x > 1 - self.radius):
            self.x = 1 - self.radius

            # Bounce off of the wall and slow down the ball
            self.velocity_x = (self.velocity_x * -1) * friction_mod
            
            # Ensure the velocity never goes below 0, so it always moves
            if abs(self.velocity_x) < min_velocity:
                self.velocity_x = -min_velocity

         # Top bounds collisions
        if (self.y > 1 - self.radius):
            self.y = 1 - self.radius

            # Bounce off of the wall and slow down the ball
            self.velocity_y = (self.velocity_y * -1) * friction_mod
            
            # Ensure the velocity never goes below 0, so it always moves
            if abs(self.velocity_y) < min_velocity:
                self.velocity_y = -min_velocity

        # Floor bounds collisions
        if (self.y < -1 + self.radius):
            # When the ball touches the bottom of the screen
            # A life is lost and the ball is disabled
            self.onoff = OnOff.OFF
            lives -= 1

            # If the player has no lives left, return to the main menu
            if lives <= 0:
                # Save the current score and push to the high score database
                score_db = PlayerScore(player_name, score, current_level)
                score_db.save_to_database()

                current_state = "MENU"
            # Else, allow the player to launch a new ball
            else:
                can_launch = True

    def draw_ball(self):
        # Only render the ball if it is "on" (not destroyed)
        if (self.onoff == OnOff.ON):
            glColor3f(self.red, self.green, self.blue)
            glBegin(GL_POLYGON)
            for i in range(360):
                deg_in_rad = i * DEG2RAD
                glVertex2f((math.cos(deg_in_rad) * self.radius) + self.x,
                           (math.sin(deg_in_rad) * self.radius) + self.y)

            glEnd()

def load_level(level):
    global active_bricks, world, can_launch, current_state, player_name, score
    active_bricks.clear()
    world.clear()
    can_launch = True

    if level == 1:
        # Place bricks on the screen in a smiley face pattern
        # The first two values are the x and y coordinates,
        # the third value is the width of the brick,
        # followed by RGB color values
        # and the last is the number of hits required to destroy the brick

        # Smiley face eyes
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.4, 0.6, 0.3, 0.22, 0.72, 0.22, 2))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.4, 0.6, 0.3, 0.22, 0.72, 0.22, 2))

        # Smiley face mouth
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.6, -0.1, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.4, -0.3, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.2, -0.5, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0, -0.5, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.2, -0.5, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.4, -0.3, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.6, -0.1, 0.2, 0.96, 0.68, 0.75, 1))

        # Smiley face nose
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0, 0.2, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.1, 0.1, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.2, 0, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.1, -0.1, 0.1, 0.99, 0.95, 0.77, 1))

        # Corner bricks
        active_bricks.append(Brick(BrickType.REFLECTIVE, -0.95, 0.95, 0.1, 0.72, 0, 1, 1))
        active_bricks.append(Brick(BrickType.REFLECTIVE, 0.95, 0.95, 0.1, 0.1, 0.23, 0.97, 1))
        active_bricks.append(Brick(BrickType.REFLECTIVE, -0.95, -0.95, 0.1, 0.11, 0.7, 0.36, 1))
        active_bricks.append(Brick(BrickType.REFLECTIVE, 0.95, -0.95, 0.1, 1, 1, 0, 1))

    elif level == 2:
        # Two rows of bricks
        # The first row requires 2 hit to destroy
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.4, 0.1, 0.2, 0.22, 0.72, 0.22, 2))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.0, 0.1, 0.2, 0.22, 0.72, 0.22, 2))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.4, 0.1, 0.2, 0.22, 0.72, 0.22, 2))

        # The second row requires 3 hits to destroy
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.6, 0.4, 0.2, 0.96, 0.68, 0.75, 3))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.2, 0.4, 0.2, 0.96, 0.68, 0.75, 3))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.2, 0.4, 0.2, 0.96, 0.68, 0.75, 3))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.6, 0.4, 0.2, 0.96, 0.68, 0.75, 3))

        # Corner bricks
        active_bricks.append(Brick(BrickType.REFLECTIVE, -0.95, 0.95, 0.1, 0.72, 0, 1, 1))
        active_bricks.append(Brick(BrickType.REFLECTIVE, 0.95, 0.95, 0.1, 0.1, 0.23, 0.97, 1))
        active_bricks.append(Brick(BrickType.REFLECTIVE, -0.95, -0.95, 0.1, 0.11, 0.7, 0.36, 1))
        active_bricks.append(Brick(BrickType.REFLECTIVE, 0.95, -0.95, 0.1, 1, 1, 0, 1))

    elif level == 3:
        # Frowny face pattern of bricks

        # Frowny face eyes
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.4, 0.6, 0.3, 0.22, 0.72, 0.22, 3))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.4, 0.6, 0.3, 0.22, 0.72, 0.22, 3))

        # Frowny face mouth
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.6, -0.6, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.4, -0.4, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.2, -0.2, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0,    -0.2, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.2,  -0.2, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.4,  -0.4, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0.6,  -0.6, 0.2, 0.96, 0.68, 0.75, 1))

        # Frowny face nose
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, 0, 0.4, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.1, 0.3, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.2, 0.2, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BrickType.DESTRUCTABLE, -0.1, 0.1, 0.1, 0.99, 0.95, 0.77, 1))

        # Corner bricks
        active_bricks.append(Brick(BrickType.REFLECTIVE, -0.95, 0.95, 0.1, 0.72, 0, 1, 1))
        active_bricks.append(Brick(BrickType.REFLECTIVE, 0.95, 0.95, 0.1, 0.1, 0.23, 0.97, 1))
        active_bricks.append(Brick(BrickType.REFLECTIVE, -0.95, -0.95, 0.1, 0.11, 0.7, 0.36, 1))
        active_bricks.append(Brick(BrickType.REFLECTIVE, 0.95, -0.95, 0.1, 1, 1, 0, 1))

    else:
        # The player completed the final level. Return to the menu.

        # Save the current score and push to the high score database
        score_db = PlayerScore(player_name, score, current_level - 1)
        score_db.save_to_database()

        current_state = "MENU"

# Initialize the SQLite database for high scores
# Concepts for the creation of the database and table referenced from:
# https://www.tutorialspoint.com/sqlite/sqlite_python.htm
def init_database():
    # Try/except block to catch any database errors, referenced from:
    # https://www.geeksforgeeks.org/python/how-to-connect-to-sqlite-database-that-resides-in-the-memory-using-python/
    try:
        connection = sqlite3.connect("breakout_db.db")
        cursor = connection.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS player_scores
                           (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           player_name TEXT NOT NULL,
                           player_score INTEGER NOT NULL,
                           highest_level INTEGER NOT NULL,
                           timestamp TEXT NOT NULL);''')
        connection.commit()
    except Exception as e:
        print(f"Database error occurred on initialization: {e}")
    finally:
        connection.close()

# Define the data structure for the player score
# This will be pushed to a MySQL database that holds high scores
# This will be expanded upon for the Databases enhancement
class PlayerScore:
    def __init__(self, player_name, player_score, highest_level):
        self.id = None
        self.player_name = player_name
        self.player_score = player_score
        self.highest_level = highest_level
        self.timestamp = None

    def save_to_database(self):
        # Get the timestamp via datetime
        self.timestamp = str(datetime.datetime.now())

        # Sanitize the player name to prevent SQL injection
        # This is for the security mindset capstone requirement
        # Remove illegal characters from the player name
        sanitized_name = self.player_name.strip()
        sanitized_name = sanitized_name.replace("'", "")
        sanitized_name = sanitized_name.replace('"', "")
        sanitized_name = sanitized_name.replace(";", "")
        sanitized_name = sanitized_name.replace("--", "")

        # Attempt to connect to the database
        try:
            connection = sqlite3.connect("breakout_db.db")
            cursor = connection.cursor()

            # Query player_scores table to check if the player already exists
            # Bind the queried data to ? to prevent SQL injection
            # "Always use [?] instead of string formatting to bind Python
            # values to SQL statements, to avoid SQL injection attacks" source:
            # https://docs.python.org/3/library/sqlite3.html
            cursor.execute('''SELECT player_score FROM player_scores WHERE player_name = ?''',
                           (sanitized_name,))
            existing_score = cursor.fetchone()

            # If no score for the player exists
            if existing_score is None:
                # Insert the new player score
                cursor.execute('''INSERT INTO player_scores (player_name,
                                                             player_score,
                                                             highest_level,
                                                             timestamp)
                               VALUES (?, ?, ?, ?)''', (sanitized_name,
                                                        self.player_score,
                                                        self.highest_level,
                                                        self.timestamp))
            # Else if the player already exists in the database
            # So update their score if it's higher
            elif self.player_score > existing_score[0]:
                # Update the existing player score if it's higher
                cursor.execute('''UPDATE player_scores SET player_score = ?,
                               highest_level = ?,
                               timestamp = ? WHERE player_name = ?''',
                               (self.player_score,
                                self.highest_level,
                                self.timestamp,
                                sanitized_name))
            
            connection.commit()
        except Exception as e:
            print(f"Database error occurred during save: {e}")
        finally:
            connection.close()

        print(f"FINAL SCORE | Player Name: {sanitized_name}, "
              f"Score: {self.player_score}, "
              f"Level: {self.highest_level}, "
              f"Timestamp: {self.timestamp}")

# Fetch the top 10 high scores from the database
def get_high_scores():
    scores = []
    # Attempt to connect to the database
    try:
        connection = sqlite3.connect("breakout_db.db")
        cursor = connection.cursor()

        # Select the top 10 entries in player_score in descending order
        cursor.execute('''SELECT player_name,
                       player_score,
                       highest_level,
                       timestamp FROM player_scores
                       ORDER BY player_score DESC LIMIT 10''')
        scores = cursor.fetchall()
    except Exception as e:
        print(f"Database error occurred while fetching high scores: {e}")
    finally:
        connection.close()
    
    # Return the top 10 high scores
    return scores

# Delete all high scores from the database
def delete_all_scores():
    # Attempt to connect to the database
    try:
        connection = sqlite3.connect("breakout_db.db")
        cursor = connection.cursor()

        # Delete all entries from the player_scores table
        cursor.execute('''DELETE FROM player_scores''')
        connection.commit()
    except Exception as e:
        print(f"Database error occurred while deleting scores: {e}")
    finally:
        connection.close()

# Define a paddle for the player to use to launch and reflect balls at position
paddle = Paddle(0, -0.9)

def main():
    global player_name

    random.seed(time.time())

    # Initialize the database for high scores
    init_database()
    
    if not glfw.init():
        # Exit the program if GLFW initialization fails and report error
        sys.exit(1)
    
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
    window = glfw.create_window(600, 600,
                                "Sam's Cool Breakout-like Game", None, None)
    if not window:
        glfw.terminate()
        sys.exit(1)

    glfw.make_context_current(window)
    glfw.swap_interval(1)

    # Initialize ImGui for GLFW
    imgui.create_context()
    impl = GlfwRenderer(window)

    while not glfw.window_should_close(window):
        global current_state, score, lives, current_level, active_bricks

        # Setup View
        width, height = glfw.get_framebuffer_size(window)
        ratio = width / float(height)
        glViewport(0, 0, width, height)
        glClear(GL_COLOR_BUFFER_BIT)

        # Start a new ImGui frame
        # This allows us to draw OpenGL GUI elements
        impl.process_inputs()
        imgui.new_frame()

        # Menu loop
        if current_state == "MENU":
            imgui.begin("Main Menu")
            
            # Go to the name entry screen before starting the game
            if imgui.button("Start Game"):
                current_state = "NAME_ENTRY"
            
            # Go to the high scores screen
            if imgui.button("High Scores"):
                high_scores = get_high_scores()
                current_state = "HIGH_SCORES"

            # Quit the game
            if imgui.button("Quit"):
                glfw.set_window_should_close(window, True)
            
            imgui.end()

        # Name entry loop
        if current_state == "NAME_ENTRY":
            imgui.begin("Enter Name")

            # Input text field for the player to enter their name
            # pyimgui reference for input text used here:
            # https://pyimgui.readthedocs.io/en/latest/reference/imgui.core.html
            changed, player_name = imgui.input_text('##Player', player_name)
            
            # Confirm the entered name and start the game
            if imgui.button("Start Game"):
                score = 0
                lives = 5
                current_level = 1
                paddle.x = 0
                load_level(current_level)
                current_state = "PLAYING"

            # Return to the main menu
            if imgui.button("Back to Main Menu"):
                current_state = "MENU"
            
            imgui.end()

        # Game loop
        if current_state == "PLAYING":
            # Render the GUI for the score and lives
            # Used ImGui reference for flags and positioning here:
            # https://github.com/pthom/imgui_bundle/blob/main/bindings/imgui_bundle/demos_python/demo_imgui_bundle_intro.py
            imgui.set_next_window_pos(imgui.ImVec2(10, 10))
            imgui.set_next_window_bg_alpha(0.0) 
            imgui_flags = (imgui.WindowFlags_.no_title_bar |
                           imgui.WindowFlags_.no_resize |
                           imgui.WindowFlags_.no_move |
                           imgui.WindowFlags_.always_auto_resize)

            imgui.begin("GUI", flags = imgui_flags)
            imgui.text(f"Score: {score} | Lives: {lives} | Level: {current_level}")
            imgui.end()

            process_input(window)

            # Check progress for level completion
            bricks_remaining = 0
            for brick in active_bricks:
                # Only count bricks that are still "on" (not destroyed)
                # and bricks that are destructible
                if (brick.onoff == OnOff.ON
                    and brick.brick_type == BrickType.DESTRUCTABLE):
                    bricks_remaining += 1

            # If all destructible bricks are destroyed, advance to the next level
            if bricks_remaining == 0:
                current_level += 1
                load_level(current_level)

            # Movement
            for i in range(len(world)):
                # Check collision on bricks
                for brick in active_bricks:
                    world[i].check_collision(brick)
                
                # Check collision on the paddle
                world[i].check_collision(paddle)
                
                world[i].move_one_step()
                world[i].draw_ball()

            # Draw bricks
            for brick in active_bricks:
                brick.draw_brick()

            # Draw the paddle
            paddle.draw_paddle()

        # High scores loop
        if current_state == "HIGH_SCORES":
            # Set the window size and position
            # It needs to be bigger than the default size to fit
            # all the possible high scores
            imgui.set_next_window_size(imgui.ImVec2(570, 570))
            imgui.set_next_window_pos(imgui.ImVec2(15, 15))

            imgui.begin("High Scores")
            
            # Draw text and separator for the high scores window
            imgui.text("Top 10 High Scores:")
            imgui.separator()

            # Display a note if there are no high scores in the database
            if (len(high_scores) == 0):
                imgui.text("No high scores recorded!")
            # Else, display the top 10 high scores
            else:
                # Scores are tuples, display by row
                rank = 1
                for row in high_scores:
                    imgui.text(f"{rank}) {row[0]} | "
                               f"Score: {row[1]} | "
                               f"Level: {row[2]} | "
                               f"Timestamp: {row[3]}")
                    rank += 1

            # Button to wipe all high scores from the database
            if imgui.button("Wipe High Scores"):
                delete_all_scores()
                high_scores.clear()
                print("All high scores removed from the database!")
            
            # Return to the main menu
            if imgui.button("Back to Main Menu"):
                current_state = "MENU"
            
            imgui.end()

        # Render ImGui GUI elements
        imgui.render()
        impl.render(imgui.get_draw_data())

        glfw.swap_buffers(window)
        glfw.poll_events()

    # Shutdown ImGui before exit
    impl.shutdown()
    imgui.destroy_context()

    # Clean up GLFW before exit
    glfw.destroy_window(window)
    glfw.terminate()

    # Exit the program
    exit(0)

# Process keyboard input in the game window
def process_input(window):
    global can_launch
    
    if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(window, True)

    # Pressing the space bar launches a new ball
    if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
        # Only launch a new ball if the player has lives left
        if can_launch:
            r = random.random()
            g = random.random()
            b = random.random()

            # Create a new ball above the center of the paddle
            ball = Ball(paddle.x, paddle.y + 0.1,
                          0.05, 0.0, 0.01, r, g, b)
            world.append(ball)

            # Set can_launch to false because we just launched a ball
            can_launch = False
    
    # Paddle movement left with A and left arrow key
    # Used https://learnopengl.com/In-Practice/2D-Game/Levels as reference
    if (glfw.get_key(window, glfw.KEY_A) == glfw.PRESS
        or glfw.get_key(window, glfw.KEY_LEFT) == glfw.PRESS):
        
        # Only move the paddle if it's on screen
        if paddle.x > -0.8:
            paddle.x -= 0.003

    # Paddle movement right with D and right arrow key
    if (glfw.get_key(window, glfw.KEY_D) == glfw.PRESS
        or glfw.get_key(window, glfw.KEY_RIGHT) == glfw.PRESS):
        
        # Only move the paddle if it's on screen
        if paddle.x < 0.8:
            paddle.x += 0.003


if __name__ == "__main__":
    main()