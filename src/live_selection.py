import argparse
import copy
import os
import queue
import re
import subprocess
import time
import cv2
import numpy as np
import watchdog.observers
import watchdog.events

from shared import FONT, NUMBERS, error, prepare_output_path

# Import pygame last to allow `shared` to set up the environment
import pygame


class LiveSelection:

    def __init__(self, macos_autofocus):
        self.screen = None
        self.macos_autofocus = macos_autofocus

    def process_images(self, images, output, images_per_slide, scale_down):
        files = os.listdir(output)
        matches = (re.match(r'slide_(\d+)_rotation_\d\.jpg', file) for file in files)
        count = max([0, *(int(match.group(1)) for match in matches if match is not None)]) + 1

        print(f'Starting image #{count} processing...')

        original_images = copy.deepcopy(images)

        shape = images[0].shape
        width = shape[1] // scale_down // images_per_slide
        height = shape[0] // scale_down // images_per_slide
        size = max(width, height)
        rotation = 0

        if self.screen is None:
            print('Opening pygame window...')
            pygame.display.init()
            self.screen = pygame.display.set_mode((size * images_per_slide, size))
            pygame.display.set_caption(f'arrows: rotate, numbers: choose, escape: discard')
        elif self.macos_autofocus:
            print('Focusing pygame window...')
            subprocess.Popen(['osascript', '-e', 'activate application "Python"'])

        while True:
            self.screen.fill((0, 0, 0))
            for index in range(images_per_slide):
                self.screen.blit(
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
                self.screen.blit(FONT.render(str(index + 1), False, (255, 0, 0)), (size * index + 5, 5))

            self.write_text('ADVANCE SLIDE NOW', (0, 255, 0), fill=False)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.display.quit()
                    error('Pygame window closed: terminating')
                elif event.type == pygame.KEYDOWN:
                    if event.key in NUMBERS[:images_per_slide]:
                        path = os.path.join(output, f'slide_{count:04d}_rotation_{rotation % 4}.jpg')
                        print(f'Saving {path}')
                        cv2.imwrite(path, original_images[NUMBERS.index(event.key)])
                        self.write_text('Image saved', (0, 255, 0))
                        return True
                    elif event.key == pygame.K_ESCAPE:
                        print('Discarding current images')
                        self.write_text('Images discarded', (255, 0, 0))
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

    def write_text(self, text, color, fill=True):
        if fill: self.screen.fill((0, 0, 0))
        text = FONT.render(text, False, color)
        self.screen.blit(text, text.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2)))
        pygame.display.flip()

    def tick(self):
        if self.screen is None:
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.display.quit()
                error('Pygame window closed: terminating')


class FileCreatedHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def on_created(self, event):
        self.queue.put(event)
        

def main(input, output, images_per_slide, scale_down, macos_autofocus):
    prepare_output_path(output, clear=False)

    if os.listdir(output):
        print(f'Warning: output directory {output} is not empty.')

    file_created_queue = queue.Queue()
    images = []

    observer = watchdog.observers.Observer()
    observer.schedule(FileCreatedHandler(file_created_queue), input, recursive=False)
    observer.start()
    print('Watching for new files...')

    live_selection = LiveSelection(macos_autofocus)

    try:
        while True:
            if file_created_queue.empty():
                live_selection.tick()
                continue

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
                live_selection.process_images(images, output, images_per_slide, scale_down)
                images = []
    finally:
        observer.stop()
        observer.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rotates and selects images during capture.')
    parser.add_argument('-o', '--output', type=str, default='./output', help='path to output images to (default ./output)')
    parser.add_argument('-i', '--images_per_slide', type=int, default=1, help='how many images should be produced (default 1, min 1, max 9)')
    parser.add_argument('-d', '--scale_down', type=int, default=1, help='scale down factor for pygame windows (default 1, min 1)')
    parser.add_argument('-m', '--macos_autofocus', action='store_true', help='autofocus selection/rotation window when next image is ready (MacOS only) (default off)')
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
        args.macos_autofocus
    )
