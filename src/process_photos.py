import argparse
import itertools
import json
import os
import cv2
import numpy as np

from shared import error, parse_aspect_ratio, prepare_output_path, prompt_for_corners, transform_frame

# Import pygame last to allow `shared` to initialize it first
import pygame


def generate_frames(input_path, images_per_slide):
    for file_name in itertools.islice(sorted(os.listdir(input_path)), images_per_slide - 1, None, images_per_slide):
        yield cv2.imread(os.path.join(input_path, file_name))


def rotate_images(frames, scale_down):
    if not frames:
        error('No frames provided')

    height, width, _ = frames[0].shape
    size = max(width, height)
    frame_count = 0

    print('Opening pygame window for rotation...')
    screen = pygame.display.set_mode((size // scale_down, size // scale_down))
    pygame.display.set_caption(f'[1 / {len(frames)}] Use arrow keys to rotate, press space to advance')

    try:    
        while True:
            screen.fill((0, 0, 0))
            screen.blit(
                pygame.surfarray.make_surface(
                    np.flip(
                        np.rot90(cv2.cvtColor(cv2.resize(
                            frames[frame_count].astype(np.uint8),
                            dsize=(width // scale_down, height // scale_down)
                        ), cv2.COLOR_BGR2RGB)),
                        0,
                    )
                ),
                (((size - width) / 2) // scale_down, ((size - height) / 2) // scale_down),
            )

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    error('Pygame window closed: terminating')
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        frame_count += 1
                        if frame_count == len(frames):
                            return frames
                        height, width, _ = frames[frame_count].shape
                        pygame.display.set_caption(f'[{frame_count + 1} / {len(frames)}] Use arrow keys to rotate, press space to advance')
                    elif event.key == pygame.K_LEFT:
                        frames[frame_count] = np.rot90(frames[frame_count])
                        width, height = height, width
                    elif event.key == pygame.K_RIGHT:
                        frames[frame_count] = np.rot90(frames[frame_count], 3)
                        width, height = height, width
    except StopIteration:
        pass

def main(
    input_path,
    output_path,
    aspect_ratio,
    corners,
    images_per_slide,
    transform,
    rotate,
    scale_down,
):
    if not transform and not rotate:
        raise ValueError('One or both transform (-t) or rotate (-r) flags must be specified.')

    if transform:
        corners = prompt_for_corners(generate_frames(input_path, images_per_slide), scale_down) if corners is None else json.loads(corners)
        prepare_output_path(output_path)

    frames = list(generate_frames(input_path, images_per_slide))
    total_frames = len(os.listdir(input_path)) // images_per_slide

    if transform:
        for index, frame in enumerate(frames):
            print(f'Transforming frame {index + 1}/{total_frames}', end='\r')
            frames[index] = transform_frame(frame, corners, aspect_ratio)

    if rotate:
        frames = rotate_images(frames, scale_down)

    for index, transformed_frame in enumerate(frames):
        cv2.imwrite(os.path.join(output_path, f'slide_{index + 1:04d}.jpg'), transformed_frame)

    print(f'Done! {total_frames} frames saved to "{output_path}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transform all images in a directory.')
    parser.add_argument('input', type=str, help='path to the input video')
    parser.add_argument('-o', '--output', type=str, default='./output', help='path to output images to (default ./output)')
    parser.add_argument('-a', '--aspect_ratio', type=str, default='3:2', help='aspect ratio of the resulting images (default 3:2)')
    parser.add_argument('-n', '--corners', type=str, help='JSON array of corner positions of the resulting image (default None)')
    parser.add_argument('-i', '--images_per_slide', type=int, default=1, help='how many images are in the input folder per slide (default 1)')
    parser.add_argument('-t', '--transform', action='store_true', help='perform a first pass of images and transform by defining corners (default off)')
    parser.add_argument('-r', '--rotate', action='store_true', help='perform a second pass of images and rotate them with the arrow keys (default off)')
    parser.add_argument('-d', '--scale_down', type=int, default=2, help='scale down factor for pygame windows (default 2)')
    args = parser.parse_args()

    main(
        args.input,
        args.output,
        parse_aspect_ratio(args.aspect_ratio),
        args.corners,
        args.images_per_slide,
        args.transform,
        args.rotate,
        args.scale_down,
    )
