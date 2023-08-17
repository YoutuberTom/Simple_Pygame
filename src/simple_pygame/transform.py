"""
A module to transform surfaces.

Requirements
------------

- Pygame library.
"""
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = ""

import pygame
from typing import Union, Optional, Tuple, List

def fill(surface: pygame.Surface, color: Union[pygame.Color, Tuple, List], rect: Optional[Union[pygame.Rect, Tuple[int, int, int, int], List[int]]] = None, special_flags: int = 0) -> pygame.Rect:
    """
    Fill the given Surface with a solid color. If the Rect argument is given then only the area inside the specified Rect will be filled, otherwise the entire Surface will be filled.

    Parameters
    ----------

    surface: The Surface to be filled.

    color: The color to fill the Surface with.

    rect (optional): The Rect defining the area that should be filled. If the value is `None`, the entire Surface will be filled.

    special_flags (optional): Additional flags to customize the fill behavior.
    """
    if rect == None:
        return surface.fill(color, special_flags = special_flags)

    try:
        rect = pygame.Rect(rect) if type(rect) != pygame.Rect else rect
    except TypeError:
        raise ValueError("Invalid rect style object.") from None

    if rect.x < 0:
        rect.width, rect.x = max(0, rect.width + rect.x), 0
    if rect.y < 0:
        rect.height, rect.y = max(0, rect.height + rect.y), 0

    surface_size = surface.get_size()
    rect.width = min(max(0, rect.width), surface_size[0])
    rect.height = min(max(0, rect.height), surface_size[1])

    surface.fill(color, rect, special_flags)
    return rect

def reverse_fill(surface: pygame.Surface, color: Union[pygame.Color, Tuple, List], rect: Union[pygame.Rect, Tuple[int, int, int, int], List[int]], special_flags: int = 0) -> pygame.Rect:
    """
    Fill the area outside the specified Rect on the given Surface with a solid color.

    Parameters
    ----------

    surface: The Surface to be filled.

    color: The color to fill the Surface with.

    rect: The Rect defining the area that should not be filled.

    special_flags (optional): Additional flags to customize the fill behavior.
    """
    try:
        rect = pygame.Rect(rect) if type(rect) != pygame.Rect else rect
    except TypeError:
        raise ValueError("Invalid rect style object.") from None

    if rect.x < 0:
        rect.width, rect.x = max(0, rect.width + rect.x), 0
    if rect.y < 0:
        rect.height, rect.y = max(0, rect.height + rect.y), 0

    surface_size = surface.get_size()
    rect.width = min(max(0, rect.width), surface_size[0])
    rect.height = min(max(0, rect.height), surface_size[1])

    subsurface = surface.subsurface(rect).copy()
    surface.fill(color, special_flags = special_flags)
    surface.blit(subsurface, rect)

    if (rect.width, rect.height) == surface_size:
        return pygame.Rect(0, 0, 0, 0)

    subrect = [0, 0, *surface_size]
    if rect.width == surface_size[0] and (rect.y == 0 or rect.y + rect.height == surface_size[1]):
        if rect.y == 0:
            subrect[1] = rect.height
        subrect[3] -= rect.height
    if rect.height == surface_size[1] and (rect.x == 0 or rect.x + rect.width == surface_size[0]):
        if rect.x == 0:
            subrect[0] = rect.width
        subrect[2] -= rect.width

    return pygame.Rect(subrect)
