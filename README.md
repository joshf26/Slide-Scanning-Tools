# Slide Scanning Tools

Tools to process photos and videos of projected slides.

### Setup

1. Ensure [Python](https://www.python.org/downloads) is installed and up to date (tested using Python 3.11).
2. Install dependencies with `pip install -r requirements.txt`.

### Processing Video

Turn a video recording of a slide projector flipping through slides into a directory of photos.

#### How to Use

1. Start the script with `python src/video_to_photos.py <INPUT_PATH>` which will use default parameters.
2. Click the corners of the slide when prompted in the order: top left, top right, bottom right, bottom left.
    - The image displayed is an average of all frames loaded so far, so if you don't see a slide to reference, just wait
      until more frames are loaded.
3. Wait for the script to complete.
4. View the results in the specified output directory (defaults to `./output`).
5. View the brightness graph in the specified output path (defaults to `./brightness.png`)
    - If not all slides are captured, or duplicate slides are captured, reference the brightness graph and tweak the
      priming and capture brightness using the flags below.
    - The priming brightness should be just below the shortest peak.
    - The capture brightness should be just above the shallowest dip.

#### Example Brightness Graph With Suitable Thresholds

![Example Brightness Graph](./example_brightness.png)

#### Optional Parameters

| Name               | Flag | Default           | Description                                                                                                                                                            |
|--------------------|------|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Output             | `-o` | `./output`        | The output path. The directory will be created if it does not exist.                                                                                                   |
| Aspect Ratio       | `-r` | `3:2`             | The aspect ratio of the resulting images. This depends on the type of slides you are scanning.                                                                         |
| Priming Brightness | `-p` | `75`              | How bright the frame needs to be before priming. Too low and you may capture duplicates, too high and you may miss slides.                                             |
| Capture Brightness | `-c` | `10`              | How dim the frame needs to be before capturing. Too low and you may miss slides, too high and you may capture before the exposure has fully adjusted.                  |
| Backtrack Time     | `-b` | `50`              | How many milliseconds to backtrack when capturing. Too low and you may capture slide transitions, too high and you may capture before the exposure has fully adjusted. |
| Start Frame        | `-s` | `0`               | The frame number processing starts at.                                                                                                                                 |
| End Frame          | `-e` | `None` (no limit) | The frame number processing ends at.                                                                                                                                   |
| Corners            | `-n` | `None` (prompt)   | A JSON array of each corner. Useful for tuning other values while keeping corners constant. By default, a window will open prompting you to click each corner.         |

### Processing Photos

Crop and transform a directory of photos of a slide projector screen.

#### How to Use

1. Start the script with `python src/transform_photos.py <INPUT_PATH>` which will use default parameters.
2. Click the corners of the slide when prompted in the order: top left, top right, bottom right, bottom left.
    - The image displayed is an average of all photos loaded so far.
3. Wait for the script to complete.
4. View the results in the specified output directory (defaults to `./output`).

#### Optional Parameters

| Name             | Flag | Default         | Description                                                                                                                                                    |
|------------------|------|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Output           | `-o` | `./output`      | The output path. The directory will be created if it does not exist.                                                                                           |
| Aspect Ratio     | `-r` | `3:2`           | The aspect ratio of the resulting images. This depends on the type of slides you are scanning.                                                                 |
| Corners          | `-n` | `None` (prompt) | A JSON array of each corner. Useful for tuning other values while keeping corners constant. By default, a window will open prompting you to click each corner. |
| Images Per Slide | `-i` | `1`             | How many images in the input folder represent one slide. This is useful if your camera saves multiple photos per slide. Only the latest image will be saved.   |
