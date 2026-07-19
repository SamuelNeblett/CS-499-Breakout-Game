# Port and enhancement of 8-2 Assignment: Coding Collisions from SNHU CS-330
# Require GLFW library for OpenGL window and keyboard support
# Install GLFW using pip install glfw
# Require PyOpenGL to support OpenGL bindings, used for rendering graphics
# Install PyOpenGL using pip install PyOpenGL
# Utilized OpenGL.GL for Python reference here:
# https://pythonprogramming.net/opengl-rotating-cube-example-pyopengl-tutoria
import glfw
from OpenGL.GL import *
import sys
import random
import math
import time

DEG2RAD = 3.14159 / 180

# Define brick types
# Added direction-specific reflection bricks for the paddle
class BRICKTYPE:
    REFLECTIVE = 0
    DESTRUCTABLE = 1
    REFLECT_UP = 2
    REFLECT_UP_LEFT = 3
    REFLECT_UP_RIGHT = 4

class ONOFF:
    ON = 1
    OFF = 0

# Define the Brick class to represent each brick in the game
class Brick:
    def __init__(self, brick_type, xx, yy, ww, red, green, blue):
        self.red = red
        self.green = green
        self.blue = blue
        self.x = xx
        self.y = yy
        self.width = ww
        self.brick_type = brick_type
        self.onoff = ONOFF.ON

    def drawBrick(self):
        if self.onoff == ONOFF.ON:
            halfside = self.width / 2

            glColor3d(self.red, self.green, self.blue)
            glBegin(GL_POLYGON)

            glVertex2d(self.x + halfside, self.y + halfside)
            glVertex2d(self.x + halfside, self.y - halfside)
            glVertex2d(self.x - halfside, self.y - halfside)
            glVertex2d(self.x - halfside, self.y + halfside)

            glEnd()

class Circle:
    def __init__(self, xx, yy, rr, direction, rad, red, green, blue):
        self.x = xx
        self.y = yy
        self.radius = rr
        self.radius = rad
        self.red = red
        self.green = green
        self.blue = blue
        self.speed = 0.01
        # 1=up 2=right 3=down 4=left 5 = up right
        # 6 = up left  7 = down right  8= down left
        self.direction = direction

        self.onoff = ONOFF.ON

    # Check collision for bricks
    def CheckCollisionBrick(self, brk):
        # If the circle is off, don't check for collision
        # between circle and brick
        if (self.onoff == ONOFF.OFF):
            return

        if brk.brick_type == BRICKTYPE.REFLECTIVE:
            if ((self.x > brk.x - brk.width
                and self.x <= brk.x + brk.width)
                and (self.y > brk.y - brk.width
                and self.y <= brk.y + brk.width)):

                self.direction = self.GetRandomDirection()

                # Adding direction-based offsets to move the ball slightly
                # above the paddle so it does not get stuck
                # "Sticky paddle" issue referenced here:
                # https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-resolution
                if self.x < brk.x:
                    self.x -= 0.02
                else:
                    self.x += 0.02
                
                if self.y < brk.y:
                    self.y -= 0.02
                else:
                    self.y += 0.02

                # For the "Alter the state of the bricks upon collision" requirement
                # Increment the color of the brick by 0.1 for each color channel
                brk.red += 0.1
                brk.green += 0.1
                brk.blue += 0.1

                # Wrap each color channel around to 0 once it reaches > 1.0
                if (brk.red > 1.0):
                    brk.red = 0.0
                if (brk.green > 1.0):
                    brk.green = 0.0
                if (brk.blue > 1.0):
                    brk.blue = 0.0
        
        elif (brk.brick_type == BRICKTYPE.DESTRUCTABLE):
            if ((self.x > brk.x - brk.width
                 and self.x <= brk.x + brk.width)
                and (self.y > brk.y - brk.width
                     and self.y <= brk.y + brk.width)):

                brk.onoff = ONOFF.OFF

        elif (brk.brick_type == BRICKTYPE.REFLECT_UP
              or brk.brick_type == BRICKTYPE.REFLECT_UP_LEFT
              or brk.brick_type == BRICKTYPE.REFLECT_UP_RIGHT):

            if ((self.x > brk.x - brk.width
                 and self.x <= brk.x + brk.width) 
                and (self.y > brk.y - brk.width
                    and self.y <= brk.y + brk.width)):

                if (brk.brick_type == BRICKTYPE.REFLECT_UP):
                    self.direction = 1
                elif (brk.brick_type == BRICKTYPE.REFLECT_UP_LEFT):
                    self.direction = 6
                elif (brk.brick_type == BRICKTYPE.REFLECT_UP_RIGHT):
                    self.direction = 5

                # Move the ball slightly above the paddle
                # so it does not get stuck
                # "Sticky paddle" issue referenced here:
                # https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-resolution
                self.y = brk.y + brk.width + 0.01
    
    # Check collision for circles/balls
    # Needed for "Alter the state of the circles on collision" requirement
    def CheckCollisionCircle(self, circle):
        # If the circle is off, don't check for collision
        # between circle and circle
        if self.onoff == ONOFF.OFF:
            return

        # Function in a similar way as the destructable brick
        if ((self.x > circle.x - circle.radius
             and self.x <= circle.x + circle.radius)
            and (self.y > circle.y - circle.radius
                 and self.y <= circle.y + circle.radius)):

            # Disable the circle on collision, so it disappears
            self.onoff = ONOFF.OFF

            # Disable the other circle on collision, so it disappears
            circle.onoff = ONOFF.OFF

    def GetRandomDirection(self):
        return random.randint(1, 8)

    # NOTE: The original directions here seemed to be flipped,
    # causing balls to go in the wrong direction
    # So, I flipped several items in this function to
    # make the ball go up when it should
    def MoveOneStep(self):

        # If the circle is off, don't move the circle
        if self.onoff == ONOFF.OFF:
            return

        # Friction modifier to slow down as it hits things
        frictionMod = 0.7

        # Move up
        if self.direction == 1 or self.direction == 5 or self.direction == 6:
            # Flipped this to check top bounds
            if (self.y < 1 - self.radius):
                # Flipped to go up instead
                self.y += self.speed
            else:
                self.direction = self.GetRandomDirection()
                
                # Ensure the speed never goes below 0, so it always moves
                if self.speed < 0.001:
                    self.speed = 0.001
                else:
                    # Apply friction to slow down the ball
                    self.speed *= frictionMod

        # Move right
        if self.direction == 2 or self.direction == 5 or self.direction == 7:
            if (self.x < 1 - self.radius):
                self.x += self.speed
            else:
                self.direction = self.GetRandomDirection()
                
                # Ensure the speed never goes below 0, so it always moves
                if self.speed < 0.001:
                    self.speed = 0.001
                else:
                    # Apply friction to slow down the ball
                    self.speed *= frictionMod

        # Move down
        if self.direction == 3 or self.direction == 7 or self.direction == 8:
            if (self.y > -1 + self.radius):
                self.y -= self.speed
            else:
                self.direction = self.GetRandomDirection()
                
                # Ensure the speed never goes below 0, so it always moves
                if self.speed < 0.001:
                    self.speed = 0.001
                else:
                    # Apply friction to slow down the ball
                    self.speed *= frictionMod

        # Move left
        if self.direction == 4 or self.direction == 6 or self.direction == 8:
            if (self.x > -1 + self.radius):
                self.x -= self.speed
            else:
                self.direction = self.GetRandomDirection()
                
                # Ensure the speed never goes below 0, so it always moves
                if self.speed < 0.001:
                    self.speed = 0.001
                else:
                    # Apply friction to slow down the ball
                    self.speed *= frictionMod

    def DrawCircle(self):
        # Only render the circle if it is "on" (not destroyed)
        if (self.onoff == ONOFF.ON):
            glColor3f(self.red, self.green, self.blue)
            glBegin(GL_POLYGON)
            for i in range(360):
                degInRad = i * DEG2RAD
                glVertex2f((math.cos(degInRad) * self.radius) + self.x,
                           (math.sin(degInRad) * self.radius) + self.y)

            glEnd()

world = []

# Define a paddle using the brick as the base
# Defining it in parts so we can affect collision direction
# based on where the ball hits the paddle
paddle_center = Brick(BRICKTYPE.REFLECT_UP, 0, -0.9, 0.1, 1, 0, 0)
paddle_left = Brick(BRICKTYPE.REFLECT_UP_LEFT, -0.1, -0.9, 0.1, 1, 0, 0)
paddle_right = Brick(BRICKTYPE.REFLECT_UP_RIGHT, 0.1, -0.9, 0.1, 1, 0, 0)

def main():
    random.seed(time.time())
    
    if not glfw.init():
        # Exit the program if GLFW initialization fails and report error
        sys.exit(1)
    
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
    window = glfw.create_window(480, 480,
                                "Sam's Cool Breakout-like Game", None, None)
    if not window:
        glfw.terminate()
        sys.exit(1)

    glfw.make_context_current(window)
    glfw.swap_interval(1)

    # Place bricks on the screen in a smiley face pattern
    # The first two values are the x and y coordinates,
    # the third value is the width of the brick,
    # and the last three values are the RGB color values

    # Smiley face eyes
    brick_1 = Brick(BRICKTYPE.REFLECTIVE, -0.4, 0.6, 0.3, 0.22, 0.72, 0.22)
    brick_2 = Brick(BRICKTYPE.REFLECTIVE, 0.4, 0.6, 0.3, 0.22, 0.72, 0.22)

    # Smiley face mouth
    brick_3 = Brick(BRICKTYPE.DESTRUCTABLE, -0.6, -0.1, 0.2, 0.96, 0.68, 0.75)
    brick_4 = Brick(BRICKTYPE.DESTRUCTABLE, -0.4, -0.3, 0.2, 0.96, 0.68, 0.75)
    brick_5 = Brick(BRICKTYPE.DESTRUCTABLE, -0.2, -0.5, 0.2, 0.96, 0.68, 0.75)
    brick_6 = Brick(BRICKTYPE.DESTRUCTABLE, 0, -0.5, 0.2, 0.96, 0.68, 0.75)
    brick_7 = Brick(BRICKTYPE.DESTRUCTABLE, 0.2, -0.5, 0.2, 0.96, 0.68, 0.75)
    brick_8 = Brick(BRICKTYPE.DESTRUCTABLE, 0.4, -0.3, 0.2, 0.96, 0.68, 0.75)
    brick_9 = Brick(BRICKTYPE.DESTRUCTABLE, 0.6, -0.1, 0.2, 0.96, 0.68, 0.75)

    # Smiley face nose
    brick_10 = Brick(BRICKTYPE.DESTRUCTABLE, 0, 0.2, 0.1, 0.99, 0.95, 0.77)
    brick_11 = Brick(BRICKTYPE.DESTRUCTABLE, -0.1, 0.1, 0.1, 0.99, 0.95, 0.77)
    brick_12 = Brick(BRICKTYPE.DESTRUCTABLE, -0.2, 0, 0.1, 0.99, 0.95, 0.77)
    brick_13 = Brick(BRICKTYPE.DESTRUCTABLE, -0.1, -0.1, 0.1, 0.99, 0.95, 0.77)

    # Corner bricks
    brick_14 = Brick(BRICKTYPE.REFLECTIVE, -0.95, 0.95, 0.1, 0.72, 0, 1)
    brick_15 = Brick(BRICKTYPE.REFLECTIVE, 0.95, 0.95, 0.1, 0.1, 0.23, 0.97)
    brick_16 = Brick(BRICKTYPE.REFLECTIVE, -0.95, -0.95, 0.1, 0.11, 0.7, 0.36)
    brick_17 = Brick(BRICKTYPE.REFLECTIVE, 0.95, -0.95, 0.1, 1, 1, 0)

    while not glfw.window_should_close(window):
        # Setup View
        width, height = glfw.get_framebuffer_size(window)
        ratio = width / float(height)
        glViewport(0, 0, width, height)
        glClear(GL_COLOR_BUFFER_BIT)

        processInput(window)

        # Movement
        for i in range(len(world)):
            # Check collision on circles/balls
            for j in range(i + 1, len(world)):
                world[i].CheckCollisionCircle(world[j])
            
            # Check collision on bricks
            world[i].CheckCollisionBrick(brick_1)
            world[i].CheckCollisionBrick(brick_2)
            world[i].CheckCollisionBrick(brick_3)
            world[i].CheckCollisionBrick(brick_4)
            world[i].CheckCollisionBrick(brick_5)
            world[i].CheckCollisionBrick(brick_6)
            world[i].CheckCollisionBrick(brick_7)
            world[i].CheckCollisionBrick(brick_8)
            world[i].CheckCollisionBrick(brick_9)
            world[i].CheckCollisionBrick(brick_10)
            world[i].CheckCollisionBrick(brick_11)
            world[i].CheckCollisionBrick(brick_12)
            world[i].CheckCollisionBrick(brick_13)
            world[i].CheckCollisionBrick(brick_14)
            world[i].CheckCollisionBrick(brick_15)
            world[i].CheckCollisionBrick(brick_16)
            world[i].CheckCollisionBrick(brick_17)
            world[i].CheckCollisionBrick(paddle_center)
            world[i].CheckCollisionBrick(paddle_left)
            world[i].CheckCollisionBrick(paddle_right)
            world[i].MoveOneStep()
            world[i].DrawCircle()

        brick_1.drawBrick()
        brick_2.drawBrick()
        brick_3.drawBrick()
        brick_4.drawBrick()
        brick_5.drawBrick()
        brick_6.drawBrick()
        brick_7.drawBrick()
        brick_8.drawBrick()
        brick_9.drawBrick()
        brick_10.drawBrick()
        brick_11.drawBrick()
        brick_12.drawBrick()
        brick_13.drawBrick()
        brick_14.drawBrick()
        brick_15.drawBrick()
        brick_16.drawBrick()
        brick_17.drawBrick()
        paddle_center.drawBrick()
        paddle_left.drawBrick()
        paddle_right.drawBrick()

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.destroy_window(window)
    glfw.terminate()
    exit(0)

# Flag to track space bar state
spacePressed = False

def processInput(window):
    global spacePressed
    
    if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(window, True)

    # Pressing the space bar launches a new ball
    if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
        # Only launch a new ball if the space bar was not already pressed
        if not spacePressed:
            r = random.random()
            g = random.random()
            b = random.random()

            # Create a new ball above the center of the paddle
            B = Circle(paddle_center.x,
                       paddle_center.y + 0.1, 0.05, 1, 0.05, r, g, b)
            world.append(B)

            # Set spacePressed to true to prevent
            # multiple balls launching on one press
            spacePressed = True
    else:
        # Reset spacePressed when the space bar is released
        spacePressed = False
    # Paddle movement left with A and left arrow key
    # Used https://learnopengl.com/In-Practice/2D-Game/Levels as reference
    if (glfw.get_key(window, glfw.KEY_A) == glfw.PRESS
        or glfw.get_key(window, glfw.KEY_LEFT) == glfw.PRESS):
        paddle_center.x -= 0.003
        paddle_left.x -= 0.003
        paddle_right.x -= 0.003

    # Paddle movement right with D and right arrow key
    if (glfw.get_key(window, glfw.KEY_D) == glfw.PRESS
        or glfw.get_key(window, glfw.KEY_RIGHT) == glfw.PRESS):
        paddle_center.x += 0.003
        paddle_left.x += 0.003
        paddle_right.x += 0.003

if __name__ == "__main__":
    main()