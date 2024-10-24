import argparse
import os
import re
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

from shared import error

BORDER_WIDTH = 10
WIDTH = 640
HEIGHT = 480
FONT_SIZE = 64


def create_image(text):
    image = PIL.Image.new('RGB', (WIDTH + BORDER_WIDTH * 2, HEIGHT + BORDER_WIDTH * 2), color=(255, 0, 0))
    draw = PIL.ImageDraw.Draw(image)
    draw.rectangle([BORDER_WIDTH, BORDER_WIDTH, WIDTH + BORDER_WIDTH - 1, HEIGHT + BORDER_WIDTH - 1], fill=(255, 255, 255))
    draw = PIL.ImageDraw.Draw(image)
    font = PIL.ImageFont.load_default(FONT_SIZE)
    bbox = draw.textbbox((0, 0), text, font=font)
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    draw.text((
        (WIDTH + 2 * BORDER_WIDTH - width) // 2,
        (HEIGHT + 2 * BORDER_WIDTH - height) // 2 - bbox[1]
    ), text, font=font, fill=(0, 0, 0))

    return image


def main(output, images_per_slide):
    matches = [re.search(r'(\d+)', file) for file in os.listdir(output)]
    next_number = max([int(match.group(0)) for match in matches if match is not None] + [0]) + 1
    for i in range(next_number, next_number + images_per_slide):
        number = f'{i:05d}'
        image = create_image(number)
        path = os.path.join(output, f'DSC{number}.JPG')
        print('Saving', path)
        image.save(path)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simulates Sony Imaging Edge Desktop by adding images to a specified directory.')
    parser.add_argument('output', type=str, help='path to the output directory')
    parser.add_argument('-i', '--images_per_slide', type=int, default=1, help='how many images should be produced (default 1, min 1, max 9)')
    args = parser.parse_args()

    if args.images_per_slide < 1 or args.images_per_slide > 9:
        error('images per slide must be between 1 and 9 (inclusive)')

    main(args.output, args.images_per_slide)
