import argparse
import itertools
import json
import os
import cv2
import numpy as np

from shared import error, parse_aspect_ratio, prepare_output_path, prompt_for_corners, transform_frame

# Import pygame last to allow `shared` to initialize it first
import pygame

FONT = pygame.font.SysFont(None, 32)
NUMBERS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9)


def generate_frames(input_path, images_per_slide):
    for file_name in itertools.islice(sorted(os.listdir(input_path)), images_per_slide - 1, None, images_per_slide):
        image = cv2.imread(os.path.join(input_path, file_name))
        if image is not None:
            yield image


def set_caption(frame_count, frames):
    pygame.display.set_caption(f'[{frame_count + 1} / {len(frames)}] arrows: rotate, numbers: choose, backspace: back')


def rotate_images(frames, scale_down, images_per_slide):
    if not frames:
        error('No frames provided')

    shape = frames[0].shape
    width = shape[1] // scale_down // images_per_slide
    height = shape[0] // scale_down // images_per_slide
    size = max(width, height)
    frame_count = 0
    result = []

    print('Opening pygame window for rotation...')
    screen = pygame.display.set_mode((size * images_per_slide, size))
    set_caption(frame_count, frames)

    try:    
        while True:
            screen.fill((0, 0, 0))
            for slide_frame in range(images_per_slide):
                screen.blit(
                    pygame.surfarray.make_surface(
                        np.flip(
                            np.rot90(cv2.cvtColor(cv2.resize(
                                frames[frame_count + slide_frame].astype(np.uint8),
                                dsize=(width, height)
                            ), cv2.COLOR_BGR2RGB)),
                            0,
                        )
                    ),
                    ((size * ((slide_frame * 2) + 1) - width) / 2, (size - height) / 2),
                )
                screen.blit(FONT.render(str(slide_frame + 1), False, (255, 0, 0)), (size * slide_frame + 5, 5))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    error('Pygame window closed: terminating')
                elif event.type == pygame.KEYDOWN:
                    if event.key in NUMBERS[:images_per_slide]:
                        result.append(frames[frame_count + NUMBERS.index(event.key)])
                        frame_count += images_per_slide
                        if frame_count == len(frames):
                            return result
                        shape = frames[frame_count].shape
                        width = shape[1] // scale_down // images_per_slide
                        height = shape[0] // scale_down // images_per_slide
                        set_caption(frame_count, frames)
                    elif event.key == pygame.K_BACKSPACE and frame_count > 0:
                        result.pop()
                        frame_count -= images_per_slide
                        shape = frames[frame_count].shape
                        width = shape[1] // scale_down // images_per_slide
                        height = shape[0] // scale_down // images_per_slide
                        set_caption(frame_count, frames)
                    elif event.key == pygame.K_LEFT:
                        for slide_frame in range(images_per_slide):
                            frames[frame_count + slide_frame] = np.rot90(frames[frame_count + slide_frame])
                        width, height = height, width
                    elif event.key == pygame.K_RIGHT:
                        for slide_frame in range(images_per_slide):
                            frames[frame_count + slide_frame] = np.rot90(frames[frame_count + slide_frame], 3)
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
        error('One or both transform (-t) or rotate (-r) flags must be specified.')

    if os.path.normpath(input_path) == os.path.normpath(output_path):
        error('Input and output paths cannot be the same.')

    prepare_output_path(output_path)

    if transform:
        corners = prompt_for_corners(generate_frames(input_path, images_per_slide), scale_down, None if corners is None else json.loads(corners))

    frames = list(generate_frames(input_path, 1 if rotate else images_per_slide))
    total_frames = len(os.listdir(input_path)) // images_per_slide

    if transform:
        for index, frame in enumerate(frames):
            print(f'Transforming frame {index + 1}/{total_frames}', end='\r')
            frames[index] = transform_frame(frame, corners, aspect_ratio)

    if rotate:
        frames = rotate_images(frames, scale_down, images_per_slide)

    for index, transformed_frame in enumerate(frames):
        cv2.imwrite(os.path.join(output_path, f'slide_{index + 1:04d}.jpg'), transformed_frame)

    print(f'Done! {total_frames} frames saved to "{output_path}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transform all images in a directory.')
    parser.add_argument('input', type=str, help='path to the input video')
    parser.add_argument('-o', '--output', type=str, default='./output', help='path to output images to (default ./output)')
    parser.add_argument('-a', '--aspect_ratio', type=str, default='3:2', help='aspect ratio of the resulting images (default 3:2)')
    parser.add_argument('-n', '--corners', type=str, help='JSON array of corner positions of the resulting image (default None)')
    parser.add_argument('-i', '--images_per_slide', type=int, default=1, help='how many images are in the input folder per slide (default 1, min 1, max 9)')
    parser.add_argument('-t', '--transform', action='store_true', help='perform a first pass of images and transform by defining corners (default off)')
    parser.add_argument('-r', '--rotate', action='store_true', help='perform a second pass of images and rotate them with the arrow keys (default off)')
    parser.add_argument('-d', '--scale_down', type=int, default=2, help='scale down factor for pygame windows (default 2, min 1)')
    args = parser.parse_args()

    if args.images_per_slide < 1 or args.images_per_slide > 9:
        error('Images per slide must be between 1 and 9 (inclusive)')
    if args.scale_down < 1:
        error('Scale down must be at least 1')

    main(
        args.input,
        os.path.join(args.output, os.path.basename(os.path.normpath(args.input))),
        parse_aspect_ratio(args.aspect_ratio),
        args.corners,
        args.images_per_slide,
        args.transform,
        args.rotate,
        args.scale_down,
    )