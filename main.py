import os
import sys

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import argparse
import cv2
import numpy as np
import progress.bar
import pygame
import shutil

PRIMING_THRESHOLD = 50
CAPTURE_THRESHOLD = 3


def calculate_frame_difference(prev_frame, current_frame):
    return np.mean((cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) - cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)) ** 2)


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


def prompt_for_corners(frame, height, width):
    pygame.init()
    screen = pygame.display.set_mode((width / 2, height / 2))
    pygame.display.set_caption('Click Corners (0/4)')
    screen.blit(
        pygame.surfarray.make_surface(
            np.flip(
                np.rot90(cv2.cvtColor(cv2.resize(frame, dsize=(width // 2, height // 2)), cv2.COLOR_BGR2RGB)),
                0,
            )
        ),
        (0, 0),
    )
    pygame.display.flip()

    result = []
    while len(result) < 4:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                result.append((x * 2, y * 2))
                pygame.draw.circle(screen, (255, 0, 0), (x, y), 5)
                pygame.display.set_caption(f'Click Corners ({len(result)}/4)')
                pygame.display.update()

    pygame.quit()

    result.sort()
    return result[0], result[3], result[2], result[1]


def prepare_output_path(output_path):
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)


def extract_frames(video_path, output_dir, aspect_ratio):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f'Error opening video file: {video_path}')
        return

    frame_count = 0
    prev_frame = None
    primed = True
    corners = None
    bar = None

    while True:
        returned, frame = cap.read()
        if not returned:
            break

        if corners is None:
            corners = prompt_for_corners(frame, frame.shape[0], frame.shape[1])
            print('Corners:', corners)
            bar = progress.bar.Bar('Analyzing...', max=cap.get(cv2.CAP_PROP_FRAME_COUNT))

        transformed_frame = transform_frame(frame, corners, aspect_ratio)

        if prev_frame is not None:
            difference = calculate_frame_difference(prev_frame, transformed_frame)
            if primed and difference < CAPTURE_THRESHOLD:
                frame_filename = os.path.join(output_dir, f'frame_{frame_count:04d}.jpg')
                cv2.imwrite(frame_filename, transformed_frame)
                frame_count += 1
                primed = False
            elif difference > PRIMING_THRESHOLD:
                primed = True

        prev_frame = transformed_frame

        bar.next()

    cap.release()
    bar.finish()
    return frame_count


def parse_aspect_ratio(aspect_ratio):
    try:
        x, y = map(int, aspect_ratio.split(':'))
    except ValueError:
        print('Error parsing aspect ratio: should be in the format "x:y"')
        sys.exit(1)

    try:
        return x / y
    except ZeroDivisionError:
        print('Error parsing aspect ratio: divide by zero error')
        sys.exit(1)


def main(input_path, output_path, aspect_ratio):
    prepare_output_path(output_path)
    num_frames = extract_frames(input_path, output_path, parse_aspect_ratio(aspect_ratio))
    print(f'Done! {num_frames} frames saved to "{output_path}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Capture still slides from a video.')
    parser.add_argument('input', type=str, help='the path to the input video')
    parser.add_argument('-r', '--aspect_ratio', type=str, default='4:3', help='the aspect ratio of the resulting images (default 4:3)')
    parser.add_argument('-o', '--output', type=str, default='./output', help='the path to the image output')
    args = parser.parse_args()
    main(args.input, args.output, args.aspect_ratio)
