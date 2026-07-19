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

DEG2RAD = 3.14159 / 180

# Gloabal variables for tracking gameplay
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
    def __init__(self, brick_type, xx, yy, ww, red, green, blue, hits_remaining):
        self.red = red
        self.green = green
        self.blue = blue
        self.x = xx
        self.y = yy
        self.width = ww
        self.brick_type = brick_type
        # If hits_remaining > 1, the brick requires multiple hits to clear
        self.hits_remaining = hits_remaining
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
    def __init__(self, xx, yy, radius, direction, red, green, blue):
        self.x = xx
        self.y = yy
        self.radius = radius
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
        global score
        
        # If the circle or brick is off, don't check for collision
        if (self.onoff == ONOFF.OFF or brk.onoff == ONOFF.OFF):
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

                # Reflect balls after hitting destructible bricks
                self.direction = self.GetRandomDirection()
                # Decrement the hits remaining for the destructible brick
                brk.hits_remaining -= 1

                if brk.hits_remaining <= 0:
                    brk.onoff = ONOFF.OFF
                    # Increment score when a destructible brick is destroyed
                    score += 100
                else:
                    # Decrement the color of the brick by 0.1 for each color channel
                    brk.red -= 0.1
                    brk.green -= 0.1
                    brk.blue -= 0.1

                    # Wrap each color channel around to 0 once it reaches > 1.0
                    if (brk.red < 0.0):
                        brk.red = 1.0
                    if (brk.green < 0.0):
                        brk.green = 1.0
                    if (brk.blue < 0.0):
                        brk.blue = 1.0
                    
                    # Increment score when a destructible brick is hit
                    # but not destroyed
                    score += 20

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
    
    # Check collision for circles/ballsreq
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
        global lives, can_launch, current_state

        # If the circle is off, don't move the circle
        if self.onoff == ONOFF.OFF:
            return

        # Friction modifier to slow down as it hits things
        frictionMod = 0.5

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

        # Move down
        if self.direction == 3 or self.direction == 7 or self.direction == 8:
            if (self.y > -1 + self.radius):
                self.y -= self.speed
            else:
                # When the circle/ball touches the bottom of the screen
                # A life is lost and the ball is disabled
                self.onoff = ONOFF.OFF
                lives -= 1

                # If the player has no lives left, return to the main menu
                if lives <= 0:
                    current_state = "MENU"
                # Else, allow the player to launch a new ball
                else:
                    can_launch = True

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

def LoadLevel(level):
    global active_bricks, world, can_launch, current_state
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
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, -0.4, 0.6, 0.3, 0.22, 0.72, 0.22, 3))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, 0.4, 0.6, 0.3, 0.22, 0.72, 0.22, 3))

        # Smiley face mouth
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.6, -0.1, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.4, -0.3, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.2, -0.5, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0, -0.5, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.2, -0.5, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.4, -0.3, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.6, -0.1, 0.2, 0.96, 0.68, 0.75, 1))

        # Smiley face nose
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0, 0.2, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.1, 0.1, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.2, 0, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.1, -0.1, 0.1, 0.99, 0.95, 0.77, 1))

        # Corner bricks
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, -0.95, 0.95, 0.1, 0.72, 0, 1, 1))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, 0.95, 0.95, 0.1, 0.1, 0.23, 0.97, 1))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, -0.95, -0.95, 0.1, 0.11, 0.7, 0.36, 1))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, 0.95, -0.95, 0.1, 1, 1, 0, 1))

    elif level == 2:
        # Two rows of bricks
        # The first row requires 2 hit to destroy
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.4, 0.1, 0.2, 0.22, 0.72, 0.22, 2))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.0, 0.1, 0.2, 0.22, 0.72, 0.22, 2))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.4, 0.1, 0.2, 0.22, 0.72, 0.22, 2))

        # The second row requires 3 hits to destroy
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.6, 0.4, 0.2, 0.96, 0.68, 0.75, 3))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.2, 0.4, 0.2, 0.96, 0.68, 0.75, 3))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.2, 0.4, 0.2, 0.96, 0.68, 0.75, 3))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.6, 0.4, 0.2, 0.96, 0.68, 0.75, 3))

        # Corner bricks
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, -0.95, 0.95, 0.1, 0.72, 0, 1, 1))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, 0.95, 0.95, 0.1, 0.1, 0.23, 0.97, 1))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, -0.95, -0.95, 0.1, 0.11, 0.7, 0.36, 1))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, 0.95, -0.95, 0.1, 1, 1, 0, 1))

    elif level == 3:
        # Frowny face pattern of bricks

        # Frowny face eyes
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, -0.4, 0.6, 0.3, 0.22, 0.72, 0.22, 3))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, 0.4, 0.6, 0.3, 0.22, 0.72, 0.22, 3))

        # Frowny face mouth
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.6, -0.6, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.4, -0.4, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.2, -0.2, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0,    -0.2, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.2,  -0.2, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.4,  -0.4, 0.2, 0.96, 0.68, 0.75, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0.6,  -0.6, 0.2, 0.96, 0.68, 0.75, 1))

        # Frowny face nose
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, 0, 0.4, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.1, 0.3, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.2, 0.2, 0.1, 0.99, 0.95, 0.77, 1))
        active_bricks.append(Brick(BRICKTYPE.DESTRUCTABLE, -0.1, 0.1, 0.1, 0.99, 0.95, 0.77, 1))

        # Corner bricks
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, -0.95, 0.95, 0.1, 0.72, 0, 1, 1))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, 0.95, 0.95, 0.1, 0.1, 0.23, 0.97, 1))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, -0.95, -0.95, 0.1, 0.11, 0.7, 0.36, 1))
        active_bricks.append(Brick(BRICKTYPE.REFLECTIVE, 0.95, -0.95, 0.1, 1, 1, 0, 1))

    else:
        # The player completed the final level. Return to the menu.
        current_state = "MENU"

# Define a paddle using the brick as the base
# Defining it in parts so we can affect collision direction
# based on where the ball hits the paddle
paddle_center = Brick(BRICKTYPE.REFLECT_UP, 0, -0.9, 0.1, 1, 0, 0, 1)
paddle_left = Brick(BRICKTYPE.REFLECT_UP_LEFT, -0.1, -0.9, 0.1, 1, 0, 0, 1)
paddle_right = Brick(BRICKTYPE.REFLECT_UP_RIGHT, 0.1, -0.9, 0.1, 1, 0, 0, 1)

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
            if imgui.button("Start Game"):
                score = 0
                lives = 5
                current_level = 1
                LoadLevel(current_level)
                current_state = "PLAYING"
            
            if imgui.button("High Scores"):
                print("High Scores to be implemented later...")

            if imgui.button("Wipe High Scores"):
                print("High Scores to be implemented later...")

            if imgui.button("Quit"):
                glfw.set_window_should_close(window, True)
            
            imgui.end()

        # Menu loop
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

            processInput(window)

            # Check progress for level completion
            bricks_remaining = 0
            for brick in active_bricks:
                # Only count bricks that are still "on" (not destroyed)
                # and bricks that are destructible
                if brick.onoff == ONOFF.ON and brick.brick_type == BRICKTYPE.DESTRUCTABLE:
                    bricks_remaining += 1

            # If all destructible bricks are destroyed, advance to the next level
            if bricks_remaining == 0:
                current_level += 1
                LoadLevel(current_level)

            # Movement
            for i in range(len(world)):
                # Check collision on circles/balls
                for j in range(i + 1, len(world)):
                    world[i].CheckCollisionCircle(world[j])
            
                # Check collision on bricks
                for brick in active_bricks:
                    world[i].CheckCollisionBrick(brick)
                
                # Check collision on the parts of the paddle
                world[i].CheckCollisionBrick(paddle_center)
                world[i].CheckCollisionBrick(paddle_left)
                world[i].CheckCollisionBrick(paddle_right)
                
                world[i].MoveOneStep()
                world[i].DrawCircle()

            # Draw bricks
            for brick in active_bricks:
                brick.drawBrick()

            # Draw the paddle parts
            paddle_center.drawBrick()
            paddle_left.drawBrick()
            paddle_right.drawBrick()

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
def processInput(window):
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
            B = Circle(paddle_center.x,
                       paddle_center.y + 0.1, 0.05, 1, r, g, b)
            world.append(B)

            # Set can_launch to false because we just launched a ball
            can_launch = False
    
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