#include <GLFW\glfw3.h>
#include "linmath.h"
#include <stdlib.h>
#include <stdio.h>
#include <conio.h>
#include <iostream>
#include <vector>
#include <windows.h>
#include <time.h>

using namespace std;

const float DEG2RAD = 3.14159 / 180;

void processInput(GLFWwindow* window);

// Define brick types
// Added direction-specific reflection bricks for the paddle
enum BRICKTYPE { REFLECTIVE, DESTRUCTABLE, REFLECT_UP, REFLECT_UP_LEFT, REFLECT_UP_RIGHT};
enum ONOFF { ON, OFF };

class Brick
{
public:
	float red, green, blue;
	float x, y, width;
	BRICKTYPE brick_type;
	ONOFF onoff;

	Brick(BRICKTYPE bt, float xx, float yy, float ww, float rr, float gg, float bb)
	{
		brick_type = bt; x = xx; y = yy, width = ww; red = rr, green = gg, blue = bb;
		onoff = ON;
	};

	void drawBrick()
	{
		if (onoff == ON)
		{
			double halfside = width / 2;

			glColor3d(red, green, blue);
			glBegin(GL_POLYGON);

			glVertex2d(x + halfside, y + halfside);
			glVertex2d(x + halfside, y - halfside);
			glVertex2d(x - halfside, y - halfside);
			glVertex2d(x - halfside, y + halfside);

			glEnd();
		}
	}
};


class Circle
{
public:
	float red, green, blue;
	float radius;
	float x;
	float y;
	float speed = 0.03;
	int direction; // 1=up 2=right 3=down 4=left 5 = up right   6 = up left  7 = down right  8= down left
	ONOFF onoff;

	Circle(double xx, double yy, double rr, int dir, float rad, float r, float g, float b)
	{
		x = xx;
		y = yy;
		radius = rr;
		red = r;
		green = g;
		blue = b;
		radius = rad;
		direction = dir;
		onoff = ON;
	}

	// Check collision for bricks
	void CheckCollision(Brick* brk)
	{
		// If the circle is off, don't check for collision between circle and brick
		if (onoff == OFF)
		{
			return;
		}

		if (brk->brick_type == REFLECTIVE)
		{
			if ((x > brk->x - brk->width && x <= brk->x + brk->width) && (y > brk->y - brk->width && y <= brk->y + brk->width))
			{
				direction = GetRandomDirection();

				// Adding direction-based offsets to move the ball slightly above the paddle so it does not get stuck
				// "Sticky paddle" issue referenced here https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-resolution
				if (x < brk->x)
				{
					x -= 0.02;
				}
				else
				{
					x += 0.02;
				}

				if (y < brk->y)
				{
					y -= 0.02;
				}
				else
				{
					y += 0.02;
				}

				// For the "Alter the state of the bricks upon collision" requirement
				// Increment the color of the brick by 0.1 for each color channel
				brk->red += 0.1f;
				brk->green += 0.1f;
				brk->blue += 0.1f;

				// Wrap each color channel around to 0 once it reaches > 1.0
				if (brk->red > 1.0f)
				{
					brk->red = 0.0f;
				}
				if (brk->green > 1.0f)
				{
					brk->green = 0.0f;
				}
				if (brk->blue > 1.0f)
				{
					brk->blue = 0.0f;
				}
			}
		}
		else if (brk->brick_type == DESTRUCTABLE)
		{
			if ((x > brk->x - brk->width && x <= brk->x + brk->width) && (y > brk->y - brk->width && y <= brk->y + brk->width))
			{
				brk->onoff = OFF;
			}
		}
		else if (brk->brick_type == REFLECT_UP || brk->brick_type == REFLECT_UP_LEFT || brk->brick_type == REFLECT_UP_RIGHT)
		{
			if ((x > brk->x - brk->width && x <= brk->x + brk->width) && (y > brk->y - brk->width && y <= brk->y + brk->width))
			{
				if (brk->brick_type == REFLECT_UP)
				{
					direction = 1;
				}
				else if (brk->brick_type == REFLECT_UP_LEFT)
				{
					direction = 6;
				}
				else if (brk->brick_type == REFLECT_UP_RIGHT)
				{
					direction = 5;
				}

				// Move the ball slightly above the paddle so it does not get stuck
				// "Sticky paddle" issue referenced here https://learnopengl.com/In-Practice/2D-Game/Collisions/Collision-resolution
				y = brk->y + brk->width + 0.01;
			}
		}
	}

	// Check collision for circles/balls
	// Needed for "Alter the state of the circles on collision" requirement
	void CheckCollision(Circle* cir)
	{
		// If the circle is off, don't check for collision between circle and circle
		if (onoff == OFF)
		{
			return;
		}

		// Function in a similar way as the destructable brick
		if ((x > cir->x - cir->radius && x <= cir->x + cir->radius) && (y > cir->y - cir->radius && y <= cir->y + cir->radius))
		{
			// Disable the circle on collision, so it disappears
			onoff = OFF;
			
			// Disable the other circle on collision, so it disappears
			cir->onoff = OFF;
		}
	}

	int GetRandomDirection()
	{
		return (rand() % 8) + 1;
	}

	// NOTE: The original directions here seemed to be flipped, causing balls to go in the wrong direction
	// So, I flipped several items in this function to make the ball go up when it should
	void MoveOneStep()
	{
		// If the circle is off, don't move the circle
		if (onoff == OFF)
		{
			return;
		}

		// Friction modifier to slow down as it hits things
		float frictionMod = 0.7f;

		if (direction == 1 || direction == 5 || direction == 6)  // up
		{
			// Flipped this to check top bounds
			if (y < 1 - radius)
			{
				// Flipped to go up instead
				y += speed;
			}
			else
			{
				direction = GetRandomDirection();
				
				// Ensure the speed never goes below 0, so it always moves
				if (speed < 0.001f)
				{
					speed = 0.001f;
				}
				else
				{
					// Apply friction to slow down the ball
					speed *= frictionMod;
				}
			}
		}

		if (direction == 2 || direction == 5 || direction == 7)  // right
		{
			if (x < 1 - radius)
			{
				x += speed;
			}
			else
			{
				direction = GetRandomDirection();

				// Ensure the speed never goes below 0, so it always moves
				if (speed < 0.001f)
				{
					speed = 0.001f;
				}
				else
				{
					// Apply friction to slow down the ball
					speed *= frictionMod;
				}
			}
		}

		if (direction == 3 || direction == 7 || direction == 8)  // down
		{
			if (y > -1 + radius)
			{
				y -= speed;
			}
			else
			{
				direction = GetRandomDirection();

				// Ensure the speed never goes below 0, so it always moves
				if (speed < 0.001f)
				{
					speed = 0.001f;
				}
				else
				{
					// Apply friction to slow down the ball
					speed *= frictionMod;
				}
			}
		}

		if (direction == 4 || direction == 6 || direction == 8)  // left
		{
			if (x > -1 + radius) {
				x -= speed;
			}
			else
			{
				direction = GetRandomDirection();

				// Ensure the speed never goes below 0, so it always moves
				if (speed < 0.001f)
				{
					speed = 0.001f;
				}
				else
				{
					// Apply friction to slow down the ball
					speed *= frictionMod;
				}
			}
		}
	}

	void DrawCircle()
	{
		// Only render the circle if it is "on" (not destroyed)
		if (onoff == ON)
		{
			glColor3f(red, green, blue);
			glBegin(GL_POLYGON);
			for (int i = 0; i < 360; i++) {
				float degInRad = i * DEG2RAD;
				glVertex2f((cos(degInRad) * radius) + x, (sin(degInRad) * radius) + y);
			}
			glEnd();
		}
	}
};


vector<Circle> world;

// Define a paddle using the brick as the base
// Defining it in parts so we can affect collision direction based on where the ball hits the paddle
Brick paddleCenter(REFLECT_UP, 0, -0.9, 0.1, 1, 0, 0);
Brick paddleLeft(REFLECT_UP_LEFT, -0.1, -0.9, 0.1, 1, 0, 0);
Brick paddleRight(REFLECT_UP_RIGHT, 0.1, -0.9, 0.1, 1, 0, 0);

int main(void) {
	srand(time(NULL));

	if (!glfwInit()) {
		exit(EXIT_FAILURE);
	}
	glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 2);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 0);
	GLFWwindow* window = glfwCreateWindow(480, 480, "8-2 Assignment", NULL, NULL);
	if (!window) {
		glfwTerminate();
		exit(EXIT_FAILURE);
	}
	glfwMakeContextCurrent(window);
	glfwSwapInterval(1);

	// Place bricks on the screen in a smiley face pattern
	// The first two values are the x and y coordinates,
	// the third value is the width of the brick,
	// and the last three values are the RGB color values

	// Smiley face eyes
	Brick brick(REFLECTIVE, -0.4, 0.6, 0.3, 0.22, 0.72, 0.22);
	Brick brick2(REFLECTIVE, 0.4, 0.6, 0.3, 0.22, 0.72, 0.22);

	// Smiley face mouth
	Brick brick3(DESTRUCTABLE, -0.6, -0.1, 0.2, 0.96, 0.68, 0.75);
	Brick brick4(DESTRUCTABLE, -0.4, -0.3, 0.2, 0.96, 0.68, 0.75);
	Brick brick5(DESTRUCTABLE, -0.2, -0.5, 0.2, 0.96, 0.68, 0.75);
	Brick brick6(DESTRUCTABLE, 0, -0.5, 0.2, 0.96, 0.68, 0.75);
	Brick brick7(DESTRUCTABLE, 0.2, -0.5, 0.2, 0.96, 0.68, 0.75);
	Brick brick8(DESTRUCTABLE, 0.4, -0.3, 0.2, 0.96, 0.68, 0.75);
	Brick brick9(DESTRUCTABLE, 0.6, -0.1, 0.2, 0.96, 0.68, 0.75);

	// Smiley face nose
	Brick brick10(DESTRUCTABLE, 0, 0.2, 0.1, 0.99, 0.95, 0.77);
	Brick brick11(DESTRUCTABLE, -0.1, 0.1, 0.1, 0.99, 0.95, 0.77);
	Brick brick12(DESTRUCTABLE, -0.2, 0, 0.1, 0.99, 0.95, 0.77);
	Brick brick13(DESTRUCTABLE, -0.1, -0.1, 0.1, 0.99, 0.95, 0.77);

	// Corner bricks
	Brick brick14(REFLECTIVE, -0.95, 0.95, 0.1, 0.72, 0, 1);
	Brick brick15(REFLECTIVE, 0.95, 0.95, 0.1, 0.1, 0.23, 0.97);
	Brick brick16(REFLECTIVE, -0.95, -0.95, 0.1, 0.11, 0.7, 0.36);
	Brick brick17(REFLECTIVE, 0.95, -0.95, 0.1, 1, 1, 0);

	while (!glfwWindowShouldClose(window)) {
		//Setup View
		float ratio;
		int width, height;
		glfwGetFramebufferSize(window, &width, &height);
		ratio = width / (float)height;
		glViewport(0, 0, width, height);
		glClear(GL_COLOR_BUFFER_BIT);

		processInput(window);

		//Movement
		for (int i = 0; i < world.size(); i++)
		{
			// Check collision on circles/balls
			for (int j = i + 1; j < world.size(); j++) {
				world[i].CheckCollision(&world[j]);
			}

			//world[i].CheckCollision(&circle);
			
			// Check collision on bricks
			world[i].CheckCollision(&brick);
			world[i].CheckCollision(&brick2);
			world[i].CheckCollision(&brick3);
			world[i].CheckCollision(&brick4);
			world[i].CheckCollision(&brick5);
			world[i].CheckCollision(&brick6);
			world[i].CheckCollision(&brick7);
			world[i].CheckCollision(&brick8);
			world[i].CheckCollision(&brick9);
			world[i].CheckCollision(&brick10);
			world[i].CheckCollision(&brick11);
			world[i].CheckCollision(&brick12);
			world[i].CheckCollision(&brick13);
			world[i].CheckCollision(&brick14);
			world[i].CheckCollision(&brick15);
			world[i].CheckCollision(&brick16);
			world[i].CheckCollision(&brick17);
			world[i].CheckCollision(&paddleCenter);
			world[i].CheckCollision(&paddleLeft);
			world[i].CheckCollision(&paddleRight);
			world[i].MoveOneStep();
			world[i].DrawCircle();
		}

		brick.drawBrick();
		brick2.drawBrick();
		brick3.drawBrick();
		brick4.drawBrick();
		brick5.drawBrick();
		brick6.drawBrick();
		brick7.drawBrick();
		brick8.drawBrick();
		brick9.drawBrick();
		brick10.drawBrick();
		brick11.drawBrick();
		brick12.drawBrick();
		brick13.drawBrick();
		brick14.drawBrick();
		brick15.drawBrick();
		brick16.drawBrick();
		brick17.drawBrick();
		paddleCenter.drawBrick();
		paddleLeft.drawBrick();
		paddleRight.drawBrick();

		glfwSwapBuffers(window);
		glfwPollEvents();
	}

	glfwDestroyWindow(window);
	glfwTerminate;
	exit(EXIT_SUCCESS);
}

// Flag to track space bar state
bool spacePressed = false;

void processInput(GLFWwindow* window)
{
	if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
		glfwSetWindowShouldClose(window, true);

	// Pressing the space bar launches a new ball
	if (glfwGetKey(window, GLFW_KEY_SPACE) == GLFW_PRESS)
	{
		// Only launch a new ball if the space bar was not already pressed
		if (!spacePressed)
		{
			double r, g, b;
			r = rand() / 10000;
			g = rand() / 10000;
			b = rand() / 10000;

			// Create a new ball above the center of the paddle
			Circle B(paddleCenter.x, paddleCenter.y + 0.1, 0.05, 1, 0.05, r, g, b);
			world.push_back(B);

			// Set spacePressed to true to prevent multiple balls launching on one press
			spacePressed = true;
		}
	}
	else
	{
		// Reset spacePressed when the space bar is released
		spacePressed = false;
	}

	// Paddle movement left with A and left arrow key
	// Used https://learnopengl.com/In-Practice/2D-Game/Levels as reference
	if (glfwGetKey(window, GLFW_KEY_A) == GLFW_PRESS || glfwGetKey(window, GLFW_KEY_LEFT) == GLFW_PRESS)
	{
		paddleCenter.x -= 0.003;
		paddleLeft.x -= 0.003;
		paddleRight.x -= 0.003;
	}
	// Paddle movement right with D and right arrow key
	if (glfwGetKey(window, GLFW_KEY_D) == GLFW_PRESS || glfwGetKey(window, GLFW_KEY_RIGHT) == GLFW_PRESS)
	{
		paddleCenter.x += 0.003;
		paddleLeft.x += 0.003;
		paddleRight.x += 0.003;
	}
}