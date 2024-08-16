import cv2
import math
import matplotlib.pyplot as plt
import numpy as np
import os
import shutil
import sys

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame

CORNER_NAMES = ['Top Left', 'Top Right', 'Bottom Right', 'Bottom Left', 'Done!']
CORNER_PROMPT_SCALE = 2
CORNER_RADIUS = 5
UI_COLOR = (255, 0, 0)


def error(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def transform_frame(frame, corners, aspect_ratio):
    width = max(corners[1][0], corners[2][0]) - min(corners[0][0], corners[3][0])
    height = int(width / aspect_ratio)
    return cv2.warpPerspective(
        frame,
        cv2.getPerspectiveTransform(
            np.array(corners, dtype=np.float32),
            np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32),
        ),
        (width, height),
    )


def prompt_for_corners(frames):
    try:
        frame = next(frames).astype(np.float32)
    except StopIteration:
        error('No frames provided')

    height, width, _ = frame.shape
    frame_count = 0
    dragging = None
    draw_requested = True
    done = False

    pygame.init()
    screen = pygame.display.set_mode((width / 2, height / 2))
    pygame.display.set_caption(f'Press Enter to Submit')

    corners = [
        [width * (1 / 4), height * (1 / 4)], # Top Left
        [width * (3 / 4), height * (1 / 4)], # Top Right
        [width * (3 / 4), height * (3 / 4)], # Bottom Right
        [width * (1 / 4), height * (3 / 4)], # Bottom Left
    ]
    while not done:
        try:
            next_frame = next(frames).astype(np.float32)
            frame_count += 1
            frame += next_frame
            draw_requested = True
        except StopIteration:
            pass

        if draw_requested:
            screen.blit(
                pygame.surfarray.make_surface(
                    np.flip(
                        np.rot90(cv2.cvtColor(cv2.resize(
                            (frame / frame_count).astype(np.uint8),
                            dsize=(width // CORNER_PROMPT_SCALE, height // CORNER_PROMPT_SCALE)
                        ), cv2.COLOR_BGR2RGB)),
                        0,
                    )
                ),
                (0, 0),
            )
            scaled_corners = [(x / CORNER_PROMPT_SCALE, y / CORNER_PROMPT_SCALE) for x, y in corners]
            for index in range(len(corners)):
                position = scaled_corners[index]
                next_position = scaled_corners[index + 1] if index < len(corners) - 1 else scaled_corners[0]
                pygame.draw.circle(screen, UI_COLOR, position, CORNER_RADIUS)
                pygame.draw.line(screen, UI_COLOR, position, next_position)

            pygame.display.flip()
            draw_requested = False

        for event in pygame.event.get():
            x, y = pygame.mouse.get_pos()
            if event.type == pygame.QUIT:
                pygame.quit()
                error('Pygame window closed: terminating')
            elif event.type == pygame.MOUSEBUTTONDOWN:
                try:
                    dragging = next(index for index in range(4) if math.dist(corners[index], [x * CORNER_PROMPT_SCALE, y * CORNER_PROMPT_SCALE]) <= CORNER_RADIUS * 2)
                except StopIteration:
                    dragging = None
            elif event.type == pygame.MOUSEBUTTONUP:
                dragging = None
            elif event.type == pygame.MOUSEMOTION and dragging is not None:
                corners[dragging] = [x * CORNER_PROMPT_SCALE, y * CORNER_PROMPT_SCALE]
                draw_requested = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    done = True

    pygame.quit()

    print(f'''Run again with the following flag to use the same corners: "-n '{corners}'"''')
    return corners


def prepare_output_path(output_path):
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)


def parse_aspect_ratio(aspect_ratio):
    try:
        x, y = map(int, aspect_ratio.split(':'))
    except ValueError:
        error('Error parsing aspect ratio: should be in the format "x:y"')

    try:
        return x / y
    except ZeroDivisionError:
        error('Error parsing aspect ratio: divide by zero error')