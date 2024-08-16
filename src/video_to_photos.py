import argparse
import contextlib
import cv2
import json
import math
import matplotlib.pyplot as plt
import numpy as np
import os

from shared import error, parse_aspect_ratio, prepare_output_path, prompt_for_corners, transform_frame


@contextlib.contextmanager
def open_video(path, start_frame):
    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        error(f'Error opening video file: {path}')
    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    yield capture
    capture.release()


def generate_frames(video_path, start_frame):
    with open_video(video_path, start_frame) as capture:
        while True:
            returned, frame = capture.read()
            if not returned:
                return
            yield frame


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


def save_brightness_graph(frame_brightness, brightness_graph, priming_brightness, capture_brightness):
    plt.plot(frame_brightness)
    plt.xlabel('Frame')
    plt.ylabel('Brightness')
    plt.yticks(np.arange(0, 255, step=8))
    plt.axhline(priming_brightness, label=f'Priming Brightness ({priming_brightness})', color='red')
    plt.axhline(capture_brightness, label=f'Capture Brightness ({capture_brightness})', color='gray')
    plt.title('Brightness')
    plt.legend()
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


    corners = prompt_for_corners(generate_frames(input_path, start_frame)) if corners is None else json.loads(corners)
    prepare_output_path(output_path)
    frame_count, total_frames, frame_brightness = extract_frames(
        input_path,
        output_path,
        aspect_ratio,
        priming_brightness,
        capture_brightness,
        backtrack_time,
        corners,
        start_frame,
        end_frame,
    )

    save_brightness_graph(frame_brightness, brightness_graph, priming_brightness, capture_brightness)

    print(f'Done! {frame_count}/{total_frames} frames saved to "{output_path}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Capture still slides from a video.')
    parser.add_argument('input', type=str, help='path to the input video')
    parser.add_argument('-o', '--output', type=str, default='./output', help='path to output images to (default ./output)')
    parser.add_argument('-g', '--brightness_graph', type=str, default='./brightness.png', help='path to output brightness graphs to (default ./brightness.png)')
    parser.add_argument('-r', '--aspect_ratio', type=str, default='3:2', help='aspect ratio of the resulting images (default 3:2)')
    parser.add_argument('-p', '--priming_brightness', type=int, default=75, help='minimum brightness required to prime the capture (default 75)')
    parser.add_argument('-c', '--capture_brightness', type=int, default=15, help='maximum brightness required to capture once primed (default 10)')
    parser.add_argument('-b', '--backtrack_time', type=int, default=50, help='number of milliseconds to backtrack when capturing (default 50)')
    parser.add_argument('-s', '--start_frame', type=int, default=0, help='frame number processing starts at (default 0)')
    parser.add_argument('-e', '--end_frame', type=int, help='frame number processing ends at (default None)')
    parser.add_argument('-n', '--corners', type=str, help='JSON array of corner positions of the resulting image (default None)')
    args = parser.parse_args()

    main(
        args.input,
        args.output,
        args.brightness_graph,
        parse_aspect_ratio(args.aspect_ratio),
        args.priming_brightness,
        args.capture_brightness,
        args.backtrack_time,
        args.start_frame,
        args.end_frame,
        args.corners,
    )
