import os
import sys

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import argparse
import cv2
import numpy as np
import pygame
import shutil

CORNER_NAMES = ['Top Left', 'Top Right', 'Bottom Right', 'Bottom Left', 'Done!']


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


def prompt_for_corners(frame):
    height, width, _ = frame.shape

    pygame.init()
    screen = pygame.display.set_mode((width / 2, height / 2))
    pygame.display.set_caption(f'Click {CORNER_NAMES[0]} Corner (0/4)')
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
                pygame.quit()
                print('Pygame window closed: terminating')
                sys.exit(0)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                result.append((x * 2, y * 2))
                pygame.draw.circle(screen, (255, 0, 0), (x, y), 5)
                pygame.display.set_caption(f'Click {CORNER_NAMES[len(result)]} Corner ({len(result)}/4)')
                pygame.display.update()

    pygame.quit()

    return result


def get_average_frame(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f'Error opening video file: {video_path}')
        return

    frame_count = 0
    result = None

    while True:
        returned, frame = cap.read()
        if not returned or frame_count > 200:
            break

        frame = frame.astype(np.float32)

        if result is None:
            result = frame
        else:
            result += frame

        frame_count += 1

    cap.release()

    return (result / frame_count).astype(np.uint8)


def prepare_output_path(output_path):
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)


def extract_frames(video_path, output_dir, aspect_ratio, corners, priming_threshold, capture_threshold, frames_required_for_capture, differences_file = None):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f'Error opening video file: {video_path}')
        return

    frame_number = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = 0
    prev_frame = None
    primed = True
    frames_above_capture_threshold = 0

    while True:
        returned, frame = cap.read()
        if not returned:
            break

        transformed_frame = transform_frame(frame, corners, aspect_ratio)

        if prev_frame is not None:
            difference = calculate_frame_difference(prev_frame, transformed_frame)
            if differences_file is not None:
                differences_file.write(str(difference) + '\n')
            if primed and difference < capture_threshold:
                frames_above_capture_threshold += 1
                if frames_above_capture_threshold > frames_required_for_capture:
                    frame_filename = os.path.join(output_dir, f'frame_{frame_count:04d}.jpg')
                    cv2.imwrite(frame_filename, transformed_frame)
                    frame_count += 1
                    frames_above_capture_threshold = 0
                    primed = False
            elif difference > priming_threshold:
                frames_above_capture_threshold = 0
                primed = True

        prev_frame = transformed_frame
        frame_number += 1
        print(f'Processing frame {frame_number}/{total_frames}', end='\r')

    cap.release()
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


def main(input_path, output_path, aspect_ratio, differences_path, priming_threshold, capture_threshold, frames_required_for_capture):
    corners = prompt_for_corners(get_average_frame(input_path))
    print(f'Corners: {corners}')
    prepare_output_path(output_path)
    if differences_path is None:
        num_frames = extract_frames(
            input_path,
            output_path,
            parse_aspect_ratio(aspect_ratio),
            corners,
            priming_threshold,
            capture_threshold,
            frames_required_for_capture,
        )
    else:
        with open(differences_path, 'w') as differences_file:
            num_frames = extract_frames(
                input_path,
                output_path,
                parse_aspect_ratio(aspect_ratio),
                corners,
                priming_threshold,
                capture_threshold,
                frames_required_for_capture,
                differences_file,
            )
        print(f'Differences saved to {differences_path}')
    print(f'Done! {num_frames} frames saved to "{output_path}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Capture still slides from a video.')
    parser.add_argument('input', type=str, help='path to the input video')
    parser.add_argument('-r', '--aspect_ratio', type=str, default='4:3', help='aspect ratio of the resulting images (default 4:3)')
    parser.add_argument('-o', '--output', type=str, default='./output', help='path to the image output (default ./output)')
    parser.add_argument('-d', '--differences', type=str, help='path to export a list of frame differences (default None)')
    parser.add_argument('-p', '--priming_threshold', type=int, default=50, help='minimum difference to prime for capture (default 50)')
    parser.add_argument('-c', '--capture_threshold', type=int, default=2, help='maximum difference to capture once primed (default 2)')
    parser.add_argument('-f', '--frames_required_for_capture', type=int, default=5, help='number of frames under the capture threshold needed to capture (default 5)')
    args = parser.parse_args()
    main(args.input, args.output, args.aspect_ratio, args.differences, args.priming_threshold, args.capture_threshold, args.frames_required_for_capture)
