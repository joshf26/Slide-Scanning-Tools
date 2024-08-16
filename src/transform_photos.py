import argparse
import itertools
import json
import os
import cv2

from shared import parse_aspect_ratio, prepare_output_path, prompt_for_corners, transform_frame


def generate_frames(input_path):
    for file_name in sorted(os.listdir(input_path)):
        yield cv2.imread(os.path.join(input_path, file_name))


def main(
    input_path,
    output_path,
    aspect_ratio,
    corners,
    images_per_slide,
):
    corners = prompt_for_corners(generate_frames(input_path)) if corners is None else json.loads(corners)
    prepare_output_path(output_path)

    total_frames = len(os.listdir(input_path)) // images_per_slide

    for index, frame in enumerate(itertools.islice(generate_frames(input_path), images_per_slide - 1, None, images_per_slide)):
        print(f'Processing frame {index + 1}/{total_frames}', end='\r')
        transformed = transform_frame(frame, corners, aspect_ratio)
        cv2.imwrite(os.path.join(output_path, f'slide_{index + 1:04d}.jpg'), transformed)

    print(f'Done! {total_frames} frames saved to "{output_path}"')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transform all images in a directory.')
    parser.add_argument('input', type=str, help='path to the input video')
    parser.add_argument('-o', '--output', type=str, default='./output', help='path to output images to (default ./output)')
    parser.add_argument('-r', '--aspect_ratio', type=str, default='3:2', help='aspect ratio of the resulting images (default 3:2)')
    parser.add_argument('-n', '--corners', type=str, help='JSON array of corner positions of the resulting image (default None)')
    parser.add_argument('-i', '--images_per_slide', type=int, help='how many images are in the input folder per slide (default 1)')
    args = parser.parse_args()

    main(
        args.input,
        args.output,
        parse_aspect_ratio(args.aspect_ratio),
        args.corners,
        args.images_per_slide,
    )
