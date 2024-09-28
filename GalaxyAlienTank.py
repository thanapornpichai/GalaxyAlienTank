import pygame
import pygame_gui
import random

WIDTH = 1280
HEIGHT = 720
MAX_SPEED = 2
NUMBER_AGENT = 20

COHERENCE_FACTOR = 0.01
ALIGNMENT_FACTOR = 0.1
SEPARATION_FACTOR = 0.05
SEPARATION_DIST = 25

HUNGER_DECREASE_RATE = 10
HUNGER_THRESHOLD = 30
HUNGER_TIME_MAX = 100
AGENT_HUNGER_MAX = 100
FOOD_RADIUS = 10
OBSTACLE_AVOIDANCE_RADIUS = 50


# -----------------------------------------------------------------------
# Food class
# -----------------------------------------------------------------------
class Food:
    def __init__(self, x, y):
        self.position = pygame.Vector2(x, y)
        self.radius = FOOD_RADIUS

    def draw(self, screen):
        screen.blit(food_sprite, self.position - pygame.Vector2(food_sprite.get_width() // 2, food_sprite.get_height() // 2))


# -----------------------------------------------------------------------
# Obstacle class
# -----------------------------------------------------------------------
class Obstacle:
    def __init__(self, x, y, sprite):
        self.sprite = sprite
        self.position = pygame.Vector2(x, y)
        self.rect = self.sprite.get_rect(center=self.position)

    def draw(self, screen):
        screen.blit(self.sprite, self.rect.topleft)


# -----------------------------------------------------------------------
# Agent class
# -----------------------------------------------------------------------

class Agent:
    def __init__(self, x, y) -> None:
        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(
            random.uniform(-MAX_SPEED, MAX_SPEED), random.uniform(-MAX_SPEED, MAX_SPEED))
        self.acceleration = pygame.Vector2(0, 0)
        self.mass = 1
        self.hunger = 30
        self.hunger_time = 0
        self.frame_size = 64
        self.fx = 0
        self.fy = 1
        self.range_radius = 100

        self.normal_sprite = agent_sprite
        self.hungry_sprite = hungry_agent_sprite

        self.agent_frame = self.normal_sprite.subsurface(pygame.Rect(self.fx * self.frame_size,
                                                                     self.fy * self.frame_size,
                                                                     self.frame_size,
                                                                     self.frame_size))
        self.time = 0
        self.animation_frame_rate = 4

    def update_animation(self):
        if self.hunger <= HUNGER_THRESHOLD:
            current_sprite = self.hungry_sprite
        else:
            current_sprite = self.normal_sprite

        if self.time > self.animation_frame_rate:
            self.fx = self.fx + 1
            self.fx = self.fx % 4
            self.agent_frame = current_sprite.subsurface(pygame.Rect(self.fx * self.frame_size,
                                                                     self.fy * self.frame_size,
                                                                     self.frame_size,
                                                                     self.frame_size))
            self.time = 0
        else:
            self.time = self.time + 1

    def update_physics(self):
        self.velocity += self.acceleration
        if self.velocity.length() > MAX_SPEED:
            self.velocity = self.velocity.normalize() * MAX_SPEED
        self.position += self.velocity
        self.acceleration = pygame.Vector2(0, 0)

    def update_hunger(self):
        self.hunger_time += 1
        if self.hunger_time >= HUNGER_TIME_MAX:
            self.hunger = max(0, self.hunger - HUNGER_DECREASE_RATE)
            self.hunger_time = 0

    def update(self, agents, foods, obstacles):
        if self.hunger <= HUNGER_THRESHOLD:
            nearby_food = self.find_in_range(foods)
            if nearby_food:
                food = self.find_food(nearby_food)
                if food:
                    self.seek(food.position)
                    if self.position.distance_to(food.position) < FOOD_RADIUS * 2.5:
                        foods.remove(food)
                        self.hunger = AGENT_HUNGER_MAX
            else:
                self.coherence(agents)
                self.separation(agents)
                self.alignment(agents)
        else:
            self.coherence(agents)
            self.separation(agents)
            self.alignment(agents)

        self.avoid_obstacles(obstacles)
        self.update_physics()
        self.update_animation()
        self.update_hunger()

    def apply_force(self, x, y):
        force = pygame.Vector2(x, y)
        self.acceleration += force / self.mass

    def seek(self, target):
        distance = target - self.position
        if distance.length() > 0:
            distance = distance.normalize() * MAX_SPEED
        self.apply_force(distance.x - self.velocity.x, distance.y - self.velocity.y)

    def coherence(self, agents):
        center_of_mass = pygame.Vector2(0, 0)
        agent_in_range_count = 0
        for agent in agents:
            if agent != self:
                distance = self.position.distance_to(agent.position)
                if distance < 100:
                    center_of_mass += agent.position
                    agent_in_range_count += 1
        if agent_in_range_count > 0:
            center_of_mass /= agent_in_range_count
            f = (center_of_mass - self.position) * COHERENCE_FACTOR
            self.apply_force(f.x, f.y)

    def separation(self, agents):
        d = pygame.Vector2(0, 0)
        for agent in agents:
            if agent != self:
                dist = self.position.distance_to(agent.position)
                if dist < SEPARATION_DIST:
                    d += self.position - agent.position
        self.apply_force(d.x * SEPARATION_FACTOR, d.y * SEPARATION_FACTOR)

    def alignment(self, agents):
        v = pygame.Vector2(0, 0)
        agent_in_range_count = 0
        for agent in agents:
            if agent != self:
                dist = self.position.distance_to(agent.position)
                if dist < 100:
                    v += agent.velocity
                    agent_in_range_count += 1
        if agent_in_range_count > 0:
            v /= agent_in_range_count
            alignment_force = v * ALIGNMENT_FACTOR
            if alignment_force:
                self.apply_force(alignment_force.x, alignment_force.y)

    def avoid_obstacles(self, obstacles):
        for obstacle in obstacles:
            obstacle_center = pygame.Vector2(obstacle.rect.center)
        
            dist_to_obstacle = self.position.distance_to(obstacle_center)

            obstacle_half_size = pygame.Vector2(obstacle.rect.width / 2, obstacle.rect.height / 2)

            if dist_to_obstacle < obstacle_half_size.length():
                avoidance_force = self.position - obstacle_center

                if avoidance_force.length() > 0:
                    avoidance_force = avoidance_force.normalize() * MAX_SPEED

                self.apply_force(avoidance_force.x * 2, avoidance_force.y * 2)


    def find_food(self, foods):
        closest_food = None
        closest_dist = float('infinity')
        for food in foods:
            dist = self.position.distance_to(food.position)
            if dist < closest_dist:
                closest_dist = dist
                closest_food = food
        return closest_food


    def find_in_range(self, items):
        in_range_items = []
        for item in items:
            if self.position.distance_to(item.position) <= self.range_radius:
                in_range_items.append(item)
        return in_range_items


    def draw(self, screen):
        screen.blit(self.agent_frame, self.position - pygame.Vector2(32, 32))
        pygame.draw.line(screen, "red", self.position, self.position + self.velocity * 10)
        pygame.draw.circle(screen, (0, 255, 0), self.position, self.range_radius, 1)


# -----------------------------------------------------------------------
#  Begin
# -----------------------------------------------------------------------
pygame.init()

# Load assets
agent_sprite = pygame.image.load("./assets/SlimeWalk.png")
background_sprite = pygame.image.load("./assets/GalaxyBG.png")
hungry_agent_sprite = pygame.image.load("./assets/SlimeHungryWalk.png")
food_sprite = pygame.image.load("./assets/StarsFood.png")
obstacle1_sprite = pygame.image.load("./assets/Obstacle1.png")
obstacle2_sprite = pygame.image.load("./assets/Obstacle2.png")

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)

gui_manager = pygame_gui.UIManager((WIDTH, HEIGHT))
speed_slider = pygame_gui.elements.UIHorizontalSlider(
    relative_rect=pygame.Rect((10, 10), (200, 20)),
    start_value=3,
    value_range=(0.0, 10.0),
    manager=gui_manager
)
separation_slider = pygame_gui.elements.UIHorizontalSlider(
    relative_rect=pygame.Rect((10, 30), (200, 20)),
    start_value=45,
    value_range=(5.0, 100.0),
    manager=gui_manager
)

agents = [Agent(random.uniform(0, WIDTH), random.uniform(0, HEIGHT))
          for _ in range(NUMBER_AGENT)]

foods = []
obstacles = [
    Obstacle(200, 200, obstacle1_sprite),
    Obstacle(1050, 550, obstacle2_sprite)
]

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = pygame.mouse.get_pos()
            foods.append(Food(x, y))

        gui_manager.process_events(event)

    screen.fill("gray")
    screen.blit(background_sprite, (0, 0))

    time_delta = clock.tick(60) / 1000.0
    gui_manager.update(time_delta)

    MAX_SPEED = speed_slider.get_current_value()
    SEPARATION_DIST = separation_slider.get_current_value()

    for agent in agents:
        agent.update(agents, foods, obstacles)
        agent.draw(screen)

    for obstacle in obstacles:
        obstacle.draw(screen)

    for food in foods:
        food.draw(screen)

    for agent in agents:
        if agent.position.x > WIDTH:
            agent.position.x = 0
        elif agent.position.x < 0:
            agent.position.x = WIDTH
        if agent.position.y > HEIGHT:
            agent.position.y = 0
        elif agent.position.y < 0:
            agent.position.y = HEIGHT

    fps = int(clock.get_fps())
    fps_text = font.render(f"FPS: {fps}", True, pygame.Color('white'))
    screen.blit(fps_text, (WIDTH - fps_text.get_width() - 10, 10))

    gui_manager.draw_ui(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
