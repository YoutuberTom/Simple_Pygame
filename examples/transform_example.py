"""
Create a window using `pygame` then use `simple_pygame.transform` on it.
"""
import simple_pygame, pygame
pygame.display.init()

if simple_pygame.TransformModule not in simple_pygame.init((simple_pygame.TransformModule,)):
    raise ImportError("Import simple_pygame.transform failed.")

if __name__ == "__main__":
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Transform test")

    black = pygame.Color(0, 0, 0)
    white = pygame.Color(255, 255, 255)

    running = True

    simple_pygame.transform.fill(screen, white)
    size = 10
    color = black
    for position in range(245, 5, -10):
        simple_pygame.transform.reverse_fill(screen, color, pygame.Rect(position, position, size, size))
        size += 20
        color = black if color == white else white
    pygame.display.update()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.display.quit()
    simple_pygame.quit((simple_pygame.TransformModule,))