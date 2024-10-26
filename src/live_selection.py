import argparse
import copy
import os
import queue
import re
import time
import cv2
import numpy as np
import watchdog.observers
import watchdog.events

from shared import error, prepare_output_path

# Import pygame last to allow `shared` to set up the environment
import pygame

pygame.font.init()
FONT = pygame.font.SysFont(None, 32)
NUMBERS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9)
QUEUE = queue.Queue()


def process_images(images, output, images_per_slide, scale_down):
    # f'slide_{count:04d}_rotation_{rotation % 4}.jpg'
    files = os.listdir(output)
    count = max(int(re.match(r'slide_(\d+)_rotation_\d\.jpg', file).group(1)) for file in files) + 1

    print(f'Starting image #{count} processing...')

    original_images = copy.deepcopy(images)

    shape = images[0].shape
    width = shape[1] // scale_down // images_per_slide
    height = shape[0] // scale_down // images_per_slide
    size = max(width, height)
    rotation = 0

    print('Opening pygame window...')
    pygame.display.init()
    screen = pygame.display.set_mode((size * images_per_slide, size))
    pygame.display.set_caption(f'arrows: rotate, numbers: choose, escape: discard')

    while True:
        screen.fill((0, 0, 0))
        for index in range(images_per_slide):
            screen.blit(
                pygame.surfarray.make_surface(
                    np.flip(
                        np.rot90(cv2.cvtColor(cv2.resize(
                            images[index].astype(np.uint8),
                            dsize=(width, height)
                        ), cv2.COLOR_BGR2RGB)),
                        0,
                    )
                ),
                ((size * ((index * 2) + 1) - width) / 2, (size - height) / 2),
            )
            screen.blit(FONT.render(str(index + 1), False, (255, 0, 0)), (size * index + 5, 5))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.display.quit()
                error('Pygame window closed: terminating')
            elif event.type == pygame.KEYDOWN:
                if event.key in NUMBERS[:images_per_slide]:
                    path = os.path.join(output, f'slide_{count:04d}_rotation_{rotation % 4}.jpg')
                    print(f'Saving {path}.')
                    cv2.imwrite(path, original_images[NUMBERS.index(event.key)])
                    pygame.display.quit()
                    return True
                elif event.key == pygame.K_ESCAPE:
                    print('Discarding current images.')
                    pygame.display.quit()
                    return False
                elif event.key == pygame.K_LEFT:
                    for index in range(images_per_slide):
                        images[index] = np.rot90(images[index])
                    width, height = height, width
                    rotation -= 1
                elif event.key == pygame.K_RIGHT:
                    for index in range(images_per_slide):
                        images[index] = np.rot90(images[index], 3)
                    width, height = height, width
                    rotation += 1


class FileCreatedHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def on_created(self, event):
        self.queue.put(event)
        

def main(input, output, images_per_slide, scale_down):
    prepare_output_path(output, clear=False)

    if os.listdir(output):
        print(f'Warning: output directory {output} is not empty.')

    file_created_queue = queue.Queue()
    images = []

    observer = watchdog.observers.Observer()
    observer.schedule(FileCreatedHandler(file_created_queue), input, recursive=False)
    observer.start()
    print('Watching for new files...')

    try:
        while True:
            event = file_created_queue.get()
            if event.is_directory or not event.src_path.endswith('.JPG'):
                print(f'Warning! Ignoring {event.src_path} because it is not a JPG.')
                return

            # Wait for the file to be fully written
            time.sleep(0.5)

            image = cv2.imread(event.src_path)

            if image is None:
                print(f'Warning! Ignoring {event.src_path} because it could not be read.')
                return

            print(f'Discovered image: {event.src_path} ({len(images) + 1}/{images_per_slide}).')
            images.append(image)

            if len(images) == images_per_slide:
                process_images(images, output, images_per_slide, scale_down)
                images = []
    finally:
        observer.stop()
        observer.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rotates and selects images during capture.')
    parser.add_argument('-o', '--output', type=str, default='./output', help='path to output images to (default ./output)')
    parser.add_argument('-i', '--images_per_slide', type=int, default=1, help='how many images should be produced (default 1, min 1, max 9)')
    parser.add_argument('-d', '--scale_down', type=int, default=1, help='scale down factor for pygame windows (default 1, min 1)')
    parser.add_argument('input', type=str, help='path to the input video')
    args = parser.parse_args()

    if args.images_per_slide < 1 or args.images_per_slide > 9:
        error('images per slide must be between 1 and 9 (inclusive)')
    if args.scale_down < 1:
        error('scale down must be at least 1')
    
    main(
        args.input,
        os.path.join(args.output, os.path.basename(os.path.normpath(args.input))),
        args.images_per_slide,
        args.scale_down,
    )
