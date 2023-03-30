"""
Play a file contains audio using the `Music` class.
"""
import simple_pygame, os, sys
successfully_imported = simple_pygame.mixer.init()

if simple_pygame.MusicClass not in successfully_imported:
    raise SystemExit("Import failed.")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        path = sys.argv[0][:-len(os.path.basename(sys.argv[0]))]
        file_path = os.path.join(path, "data", "Sound.mp3")
    else:
        file_path = sys.argv[1]

    music = simple_pygame.mixer.Music(file_path)
    music.play()
    music.join()
    
    simple_pygame.mixer.quit()
