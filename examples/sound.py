"""
Play a file contains audio using the `Sound` class.
"""
import simple_pygame, os, sys
successfully_imported = simple_pygame.mixer.init()

if simple_pygame.SoundClass not in successfully_imported:
    raise SystemExit("Import failed.")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        path = os.path.dirname(sys.argv[0])
        file_path = os.path.join(path, "data", "Sound.mp3")
    else:
        file_path = sys.argv[1]

    sound = simple_pygame.mixer.Sound(file_path)
    sound.play()

    while sound.get_busy():
        pass

    simple_pygame.mixer.quit()
