![Simple Pygame logo](https://raw.githubusercontent.com/YoutuberTom/Simple_Pygame/main/docs/images/Logo.png)

### Simple Pygame is a [Python](https://www.python.org/) library that provides many features using [Pygame](https://www.pygame.org/news) and other libraries. It can help you create multimedia applications much easier and save you a lot of time.

# **Installation:**

    pip install simple_pygame

# **Dependencies:**

## Python libraries:

| Library | Version |
|:--------|:--------|
|pygame   |>= 2.0.0 |
|moviepy  |>= 1.0.0 |
|pyaudio  |>= 0.2.11|

## Other requirements:

- ffmpeg.exe.

# **Example:**

## In this example we play a mp3 file:

    import simple_pygame
    simple_pygame.init()

    music = simple_pygame.mixer.Music("Music.mp3")
    music.play()

    while music.get_busy():
        pass
    
    exception = music.get_exception()

    if exception:
        raise exception


### **Note**: You can play any file contains audio that supported by ffmpeg.

# **License:**

### This library is distributed under [MIT license](https://github.com/YoutuberTom/Simple_Pygame/blob/main/LICENSE).
