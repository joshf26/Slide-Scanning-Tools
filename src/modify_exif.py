import argparse
import os

from shared import change_date


def main(input, year):
    files = sorted(os.listdir(input))
    for index, file in enumerate(files):
        if not file.lower().endswith(('.jpg', '.jpeg')): continue
        file_path = os.path.join(input, file)
        print('Modifying', file_path)
        change_date(file_path, year, index)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Modifies EXIF data of all files in a directory.')
    parser.add_argument('input', type=str, help='path to the input directory')
    parser.add_argument('year', type=int, help='specify a year to change image EXIF data to')
    args = parser.parse_args()

    main(
        args.input,
        args.year,
    )
