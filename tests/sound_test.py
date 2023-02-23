import simple_pygame, os
simple_pygame.init()

path = __file__[:-len(os.path.basename(__file__))]
separator = os.sep
file_path = path + fr"{separator}data{separator}Sound.mp3"

sound = simple_pygame.mixer.Sound(file_path)
sound.play()

while sound.get_busy():
    pass