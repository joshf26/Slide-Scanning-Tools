import argparse
import contextlib
import cv2
import json
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


@contextlib.contextmanager
def open_video(path, start_frame):
    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        error(f'Error opening video file: {path}')
    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    yield capture
    capture.release()


def transform_frame(frame, corners, aspect_ratio):
    width = max(corners[1][0], corners[2][0]) - min(corners[0][0], corners[3][0])
    height = int(width / aspect_ratio)
    return cv2.warpPerspective(
        frame,
        cv2.getPerspectiveTransform(
            np.array(corners, dtype=np.float32),
            np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
        ),
        (width, height)
    )


def prompt_for_corners(video_path, start_frame):
    with open_video(video_path, start_frame) as capture:
        returned, frame = capture.read()
        if not returned:
            error('Error: video contains no frames')
        frame = frame.astype(np.float32)
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
            returned, next_frame = capture.read()
            if returned:
                next_frame = next_frame.astype(np.float32)
                frame_count += 1
                frame += next_frame
                draw_requested = True

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


def extract_frames(video_path, output_dir, aspect_ratio, priming_brightness, capture_brightness, backtrack_time, corners, start_frame, end_frame):
    with open_video(video_path, start_frame) as capture:
        frames_to_backtrack = math.ceil(capture.get(cv2.CAP_PROP_FPS) / 1000 * backtrack_time)
        frame_number = 1
        video_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        total_frames = (video_frames if end_frame is None else min(end_frame, video_frames)) - start_frame
        capture_count = 0
        prev_frame = None
        primed = True
        frame_queue = []
        frame_brightness = []

        while True:
            returned, frame = capture.read()
            if not returned:
                break

            if end_frame is not None and frame_number > (end_frame - start_frame):
                break

            print(f'Processing frame {frame_number}/{total_frames} ({capture_count} captured)', end='\r')

            transformed_frame = transform_frame(frame, corners, aspect_ratio)
            brightness = np.mean(transformed_frame)
            frame_brightness.append(brightness)

            if prev_frame is not None:
                if primed:
                    if len(frame_queue) >= frames_to_backtrack and brightness < capture_brightness:
                        capture_count += 1
                        frame_filename = os.path.join(output_dir, f'slide_{capture_count:04d}.jpg')
                        cv2.imwrite(frame_filename, frame_queue[0])
                        primed = False
                    else:
                        frame_queue.append(transformed_frame)
                        if len(frame_queue) > frames_to_backtrack:
                            frame_queue.pop(0)
                elif brightness > priming_brightness:
                    frame_queue = []
                    primed = True

            prev_frame = transformed_frame
            frame_number += 1

    print()  # Flush the output
    return capture_count, total_frames, frame_brightness


def parse_aspect_ratio(aspect_ratio):
    try:
        x, y = map(int, aspect_ratio.split(':'))
    except ValueError:
        error('Error parsing aspect ratio: should be in the format "x:y"')

    try:
        return x / y
    except ZeroDivisionError:
        error('Error parsing aspect ratio: divide by zero error')


def save_brightness_graph(frame_brightness, brightness_graph):
    plt.plot(frame_brightness)
    plt.xlabel('Frame')
    plt.ylabel('Brightness')
    plt.yticks(np.arange(0, 255, step=8))
    plt.title('Brightness')
    plt.savefig(brightness_graph)
    print(f'Saved brightness graph to {brightness_graph}')


def main(
    input_path,
    output_path,
    brightness_graph,
    aspect_ratio,
    priming_brightness,
    capture_brightness,
    backtrack_time,
    start_frame,
    end_frame,
    corners,
):
    if 0 > priming_brightness or priming_brightness > 255:
        error('priming_brightness must be between 0 and 255 (inclusive)')
    if 0 > capture_brightness or capture_brightness > 255:
        error('capture_brightness must be between 0 and 255 (inclusive)')
    if 0 > backtrack_time:
        error('backtrack_time must be greater than 0')
    if 0 > start_frame:
        error('start_frame must be greater than 0')
    if end_frame is not None and end_frame < start_frame:
        error('end_frame must be greater than start_frame')


    corners = prompt_for_corners(input_path, start_frame) if corners is None else json.loads(corners)
    prepare_output_path(output_path)
    frame_count, total_frames, frame_brightness = extract_frames(
        input_path,
        output_path,
        parse_aspect_ratio(aspect_ratio),
        priming_brightness,
        capture_brightness,
        backtrack_time,
        corners,
        start_frame,
        end_frame,
    )

    save_brightness_graph(frame_brightness, brightness_graph)

    print(f'Done! {frame_count}/{total_frames} frames saved to "{output_path}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Capture still slides from a video.')
    parser.add_argument('input', type=str, help='path to the input video')
    parser.add_argument('-o', '--output', type=str, default='./output', help='path to output images to (default ./output)')
    parser.add_argument('-g', '--brightness_graph', type=str, default='./brightness.png', help='path to output brightness graphs to (default ./brightness.png)')
    parser.add_argument('-r', '--aspect_ratio', type=str, default='4:3', help='aspect ratio of the resulting images (default 4:3)')
    parser.add_argument('-p', '--priming_brightness', type=int, default=75, help='minimum brightness required to prime the capture (default 75)')
    parser.add_argument('-c', '--capture_brightness', type=int, default=10, help='maximum brightness required to capture once primed (default 10)')
    parser.add_argument('-b', '--backtrack_time', type=int, default=50, help='number of milliseconds to backtrack when capturing (default 50)')
    parser.add_argument('-s', '--start_frame', type=int, default=0, help='frame number processing starts at (default 0)')
    parser.add_argument('-e', '--end_frame', type=int, help='frame number processing ends at (default None)')
    parser.add_argument('-n', '--corners', type=str, help='JSON array of corner positions of the resulting image (default None)')
    args = parser.parse_args()

    main(
        args.input,
        args.output,
        args.brightness_graph,
        args.aspect_ratio,
        args.priming_brightness,
        args.capture_brightness,
        args.backtrack_time,
        args.start_frame,
        args.end_frame,
        args.corners,
    )
