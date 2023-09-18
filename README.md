# Slide To Photos

Capture still slides from a video.

### Setup

1. Ensure [Python](https://www.python.org/downloads) is installed and up to date (tested using Python 3.11).
2. Install dependencies with `pip install -r requirements.txt`.

### Usage

1. Start the script with `python slide_to_photo.py <INPUT_PATH>` which will use default parameters.
2. Click the corners of the slide when prompted in the order: top left, top right, bottom right, bottom left.
    - The image displayed is an average of all frames loaded so far, so if you don't see a slide to reference, just wait
      until more frames are loaded.
3. Wait for the script to complete.
4. View the results in the specified output directory (defaults to `./output`).

### Parameters

| Name               | Flag | Default           | Description                                                                                                                                                            |
|--------------------|------|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Output             | `-o` | `./output`        | The output path. The directory will be created if it does not exist.                                                                                                   |
| Aspect Ratio       | `-r` | `4:3`             | The aspect ratio of the resulting images. This depends on the type of slides you are scanning.                                                                         |
| Priming Brightness | `-p` | `75`              | How bright the frame needs to be before priming. Too low and you may capture duplicates, too high and you may miss slides.                                             |
| Capture Brightness | `-c` | `10`              | How dim the frame needs to be before capturing. Too low and you may miss slides, too high and you may capture before the exposure has fully adjusted.                  |
| Backtrack Time     | `-b` | `50`              | How many milliseconds to backtrack when capturing. Too low and you may capture slide transitions, too high and you may capture before the exposure has fully adjusted. |
| Start Frame        | `-s` | `0`               | The frame number processing starts at.                                                                                                                                 |
| End Frame          | `-e` | `None` (no limit) | The frame number processing ends at.                                                                                                                                   |
| Corners            | `-n` | `None` (prompt)   | A JSON array of each corner. Useful for tuning other values while keeping corners constant. By default, a window will open prompting you to click each corner.         |
