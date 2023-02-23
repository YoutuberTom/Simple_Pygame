import simple_pygame, os
simple_pygame.init()

path = __file__[:-len(os.path.basename(__file__))]
separator = os.sep
file_path = path + fr"{separator}data{separator}Sound.mp3"

if __name__ == "__main__":
    music = simple_pygame.mixer.Music(file_path)
    music.play()

    while music.get_busy():
        pass

    exception = music.get_exception()

    if exception:
        raise exception