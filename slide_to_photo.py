import os
import sys
import argparse
import contextlib
import cv2
import numpy as np
import shutil

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame

CORNER_NAMES = ['Top Left', 'Top Right', 'Bottom Right', 'Bottom Left', 'Done!']


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


def prompt_for_corners(video_path, start_frame):
    with open_video(video_path, start_frame) as capture:
        returned, frame = capture.read()
        if not returned:
            error('Error: video contains no frames')
        frame = frame.astype(np.float32)
        height, width, _ = frame.shape
        frame_count = 0

        pygame.init()
        screen = pygame.display.set_mode((width / 2, height / 2))
        pygame.display.set_caption(f'Click {CORNER_NAMES[0]} Corner (0/4)')

        result = []
        while len(result) < 4:
            returned, next_frame = capture.read()
            next_frame = next_frame.astype(np.float32)
            if returned:
                frame_count += 1
                frame += next_frame
                screen.blit(
                    pygame.surfarray.make_surface(
                        np.flip(
                            np.rot90(cv2.cvtColor(cv2.resize((frame / frame_count).astype(np.uint8), dsize=(width // 2, height // 2)), cv2.COLOR_BGR2RGB)),
                            0,
                        )
                    ),
                    (0, 0),
                )
                for x, y in result:
                    pygame.draw.circle(screen, (255, 0, 0), (x / 2, y / 2), 5)
                pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    error('Pygame window closed: terminating')
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = pygame.mouse.get_pos()
                    result.append((x * 2, y * 2))
                    pygame.draw.circle(screen, (255, 0, 0), (x, y), 5)
                    pygame.display.set_caption(f'Click {CORNER_NAMES[len(result)]} Corner ({len(result)}/4)')
                    pygame.display.update()

    pygame.quit()

    return result


def prepare_output_path(output_path):
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)


def extract_frames(video_path, output_dir, aspect_ratio, corners, priming_threshold, capture_threshold, frames_required_for_capture, start_frame, end_frame, differences_file = None):
    with open_video(video_path, start_frame) as capture:
        frame_number = 1
        video_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        total_frames = (video_frames if end_frame is None else min(end_frame, video_frames)) - start_frame
        frame_count = 0
        prev_frame = None
        primed = True
        frames_above_capture_threshold = 0

        while True:
            returned, frame = capture.read()
            if not returned:
                break

            if end_frame is not None and frame_number > (end_frame - start_frame):
                break

            print(f'Processing frame {frame_number}/{total_frames}', end='\r')

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

    return frame_count, total_frames


def parse_aspect_ratio(aspect_ratio):
    try:
        x, y = map(int, aspect_ratio.split(':'))
    except ValueError:
        error('Error parsing aspect ratio: should be in the format "x:y"')

    try:
        return x / y
    except ZeroDivisionError:
        error('Error parsing aspect ratio: divide by zero error')


def main(
    input_path,
    output_path,
    aspect_ratio,
    priming_threshold,
    capture_threshold,
    frames_required_for_capture,
    start_frame,
    end_frame,
    differences_path,
):
    corners = prompt_for_corners(input_path, start_frame)
    print(f'Corners: {corners}')
    prepare_output_path(output_path)
    if differences_path is None:
        frame_count, total_frames = extract_frames(
            input_path,
            output_path,
            parse_aspect_ratio(aspect_ratio),
            corners,
            priming_threshold,
            capture_threshold,
            frames_required_for_capture,
            start_frame,
            end_frame,
        )
    else:
        with open(differences_path, 'w') as differences_file:
            frame_count, total_frames = extract_frames(
                input_path,
                output_path,
                parse_aspect_ratio(aspect_ratio),
                corners,
                priming_threshold,
                capture_threshold,
                frames_required_for_capture,
                start_frame,
                end_frame,
                differences_file,
            )
        print(f'Differences saved to "{differences_path}"')
    print(f'Done! {frame_count}/{total_frames} frames saved to "{output_path}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Capture still slides from a video.')
    parser.add_argument('input', type=str, help='path to the input video')
    parser.add_argument('-o', '--output', type=str, default='./output', help='path to the image output (default ./output)')
    parser.add_argument('-r', '--aspect_ratio', type=str, default='4:3', help='aspect ratio of the resulting images (default 4:3)')
    parser.add_argument('-d', '--differences', type=str, help='path to export a list of frame differences (default None)')
    parser.add_argument('-c', '--capture_threshold', type=int, default=2, help='maximum difference to capture once primed (default 2)')
    parser.add_argument('-p', '--priming_threshold', type=int, default=50, help='minimum difference to prime for capture (default 50)')
    parser.add_argument('-f', '--frames_required_for_capture', type=int, default=5, help='number of frames under the capture threshold needed to capture (default 5)')
    parser.add_argument('-s', '--start_frame', type=int, default=0, help='the frame number processing starts at (default 0)')
    parser.add_argument('-e', '--end_frame', type=int, help='the frame number processing ends at (default None)')
    args = parser.parse_args()

    main(
        args.input,
        args.output,
        args.aspect_ratio,
        args.priming_threshold,
        args.capture_threshold,
        args.frames_required_for_capture,
        args.start_frame,
        args.end_frame,
        args.differences,
    )
