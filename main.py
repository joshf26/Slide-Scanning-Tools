import shutil
from argparse import ArgumentParser

import cv2
import os
import numpy as np

PRIMING_THRESHOLD = 50
CAPTURE_THRESHOLD = 3


def calculate_frame_difference(prev_frame, current_frame):
    return np.mean((cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) - cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)) ** 2)


def transform_frame(frame, corners):
    width = max(corners[1][0], corners[2][0]) - min(corners[0][0], corners[3][0])
    height = max(corners[2][1], corners[3][1]) - min(corners[0][1], corners[1][1])
    return cv2.warpPerspective(
        frame,
        cv2.getPerspectiveTransform(
            np.array(corners, dtype=np.float32),
            np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
        ),
        (width, height)
    )


def prepare_output_path(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def extract_frames(video_path, output_dir):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f'Error opening video file: {video_path}')
        return

    frame_count = 0
    prev_frame = None
    primed = True
    corners = None

    while True:
        returned, frame = cap.read()
        if not returned:
            break

        if prev_frame is None:
            corners = prompt_for_corners(frame, frame.shape[0], frame.shape[1])

        transformed_frame = transform_frame(frame, corners)

        if prev_frame is not None:
            difference = calculate_frame_difference(prev_frame, transformed_frame)
            print(difference)
            if primed and difference < CAPTURE_THRESHOLD:
                frame_filename = os.path.join(output_dir, f"frame_{frame_count:04d}.jpg")
                cv2.imwrite(frame_filename, transformed_frame)
                frame_count += 1
                primed = False
            elif difference > PRIMING_THRESHOLD:
                primed = True

        prev_frame = transformed_frame

    cap.release()
    print(f"Frames extracted: {frame_count}")


def prompt_for_corners(frame, height, width):
    print(f'prompt_for_corners({frame}, {height}, {width})')

    import pygame
    pygame.init()
    screen = pygame.display.set_mode((width/2, height/2))
    pygame.display.set_caption("Click Four Corners")
    screen.blit(pygame.surfarray.make_surface(np.flip(np.rot90(cv2.resize(frame, dsize=(width//2, height//2))), 0)), (0, 0))
    pygame.display.flip()

    # List to store the clicked points
    clicked_points = []

    # Main game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and len(clicked_points) < 4:
                x, y = pygame.mouse.get_pos()
                clicked_points.append((x*2, y*2))
                pygame.draw.circle(screen, (255, 0, 0), (x, y), 5)
                pygame.display.update()

        if len(clicked_points) == 4:
            running = False

    return clicked_points


def main(input_path, output_path):
    prepare_output_path(output_path)
    extract_frames(input_path, output_path)


if __name__ == "__main__":
    parser = ArgumentParser(description='Capture still slides from a video.')
    parser.add_argument('input', type=str, help='the path to the input video')
    # parser.add_argument('x1', type=int, help='the top left corner x')
    # parser.add_argument('y1', type=int, help='the top left corner y')
    # parser.add_argument('x2', type=int, help='the top right corner x')
    # parser.add_argument('y2', type=int, help='the top right corner y')
    # parser.add_argument('x3', type=int, help='the bottom right corner x')
    # parser.add_argument('y3', type=int, help='the bottom right corner y')
    # parser.add_argument('x4', type=int, help='the bottom left corner x')
    # parser.add_argument('y4', type=int, help='the bottom left corner y')
    parser.add_argument('-o', '--output', type=str, default='output', help='the path to the image output')
    args = parser.parse_args()
    main(args.input, args.output)  #, ((args.x1, args.y1), (args.x2, args.y2), (args.x3, args.y3), (args.x4, args.y4)))
