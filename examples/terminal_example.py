"""
Read keypresses from `sys.stdin` using the `terminal` module.
"""
import simple_pygame

if simple_pygame.TerminalModule not in simple_pygame.init((simple_pygame.TerminalModule,)):
    raise ImportError("Import simple_pygame.terminal failed.")

if __name__ == "__main__":
    while True:
        key = simple_pygame.terminal.getch()

        print("You just pressed:", key)
        if key == simple_pygame.terminal.Keys.Ctrl_C:
            break

    simple_pygame.quit((simple_pygame.TerminalModule,))