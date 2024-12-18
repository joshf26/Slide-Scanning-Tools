import datetime
import time
import PIL
import PIL.Image
import cv2
import math
import numpy as np
import os
import shutil
import sys

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame

pygame.font.init()
FONT = pygame.font.SysFont(None, 32)
NUMBERS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9)
CORNER_NAMES = ['Top Left', 'Top Right', 'Bottom Right', 'Bottom Left', 'Done!']
CORNER_RADIUS = 5
UI_COLOR = (255, 0, 0)


def error(message):
    print(f'Error: {message}', file=sys.stderr)
    os._exit(1)


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


def prompt_for_corners(frames, scale_down, corners=None):
    try:
        frame = next(frames).astype(np.float32)
    except StopIteration:
        error('no frames provided')

    height, width, _ = frame.shape
    frame_count = 0
    dragging = None
    draw_requested = True
    done = False

    print('Opening pygame window for corner input...')
    pygame.display.init()
    screen = pygame.display.set_mode((width // scale_down, height // scale_down))
    pygame.display.set_caption('Press enter to submit')

    if corners is None:
        corners = [
            [int(width * (1 / 4)), int(height * (1 / 4))], # Top Left
            [int(width * (3 / 4)), int(height * (1 / 4))], # Top Right
            [int(width * (3 / 4)), int(height * (3 / 4))], # Bottom Right
            [int(width * (1 / 4)), int(height * (3 / 4))], # Bottom Left
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
                            dsize=(width // scale_down, height // scale_down)
                        ), cv2.COLOR_BGR2RGB)),
                        0,
                    )
                ),
                (0, 0),
            )
            scaled_corners = [(x / scale_down, y / scale_down) for x, y in corners]
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
                pygame.display.quit()
                error('pygame window closed: terminating')
            elif event.type == pygame.MOUSEBUTTONDOWN:
                try:
                    dragging = next(index for index in range(4) if math.dist(corners[index], [x * scale_down, y * scale_down]) <= CORNER_RADIUS * 4)
                except StopIteration:
                    dragging = None
            elif event.type == pygame.MOUSEBUTTONUP:
                dragging = None
            elif event.type == pygame.MOUSEMOTION and dragging is not None:
                corners[dragging] = [x * scale_down, y * scale_down]
                draw_requested = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    done = True

    pygame.display.quit()

    print(f'''Run again with the following flag to use the same corners: "-n '{corners}'"''')
    return corners


def prepare_output_path(output_path, clear=True):
    if os.path.exists(output_path):
        if not clear:
            return

        output_files = os.listdir(output_path)
        if len(output_files) > 0 and not input(f'Warning: {output_path} has {len(output_files)} file(s) that will be deleted including "{output_files[0]}". Would you like to continue? [y/n] ').lower() == 'y':
            error('aborting')
        shutil.rmtree(output_path)
    os.makedirs(output_path)


def parse_aspect_ratio(aspect_ratio):
    try:
        x, y = map(int, aspect_ratio.split(':'))
    except ValueError:
        error('cannot parse aspect ratio: should be in the format "x:y"')

    try:
        return x / y
    except ZeroDivisionError:
        error('cannot parse aspect ratio: divide by zero error')

def change_date(file_path, year, index):
    hour = 12 + index // 60
    minute = index % 60
    new_time = datetime.datetime(year, 1, 1, hour, minute)
    new_timestamp = time.mktime(new_time.timetuple())

    # Change the OS time
    os.utime(file_path, (new_timestamp, new_timestamp))

    # Change the EXIF time
    image = PIL.Image.open(file_path)
    exif_data = image._getexif()
    if not exif_data:
        return

    exif = {PIL.ExifTags.TAGS.get(k, k): v for k, v in exif_data.items()}
    if 'DateTimeOriginal' not in exif:
        return

    exif['DateTimeOriginal'] = time.strftime("%Y:%m:%d %H:%M:%S")
    image.save(file_path)
