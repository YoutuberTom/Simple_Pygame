"""
Play a file contains audio using the `Audio` class.
"""
import simple_pygame, sys, os

if simple_pygame.AudioClass not in simple_pygame.mixer.init([simple_pygame.AudioClass]):
    raise ImportError("Import simple_pygame.mixer.Audio failed.")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        file_path = os.path.join(os.path.dirname(sys.argv[0]), "data", "Sound.mp3")
    else:
        file_path = sys.argv[1]

    audio = simple_pygame.mixer.Audio(file_path)
    audio.play()
    audio.join()
    audio.terminate()

    simple_pygame.mixer.quit([simple_pygame.AudioClass])
