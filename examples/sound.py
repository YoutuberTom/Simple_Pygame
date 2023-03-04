"""
Play a file contains audio using the `Sound` class.
"""
import simple_pygame, os
simple_pygame.init()

path = __file__[:-len(os.path.basename(__file__))]
file_path = os.path.join(path, "data", "Sound.mp3")

sound = simple_pygame.mixer.Sound(file_path)
sound.play()

while sound.get_busy():
    pass