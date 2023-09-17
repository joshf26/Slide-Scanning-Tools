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

| Name                        | Flag | Default            | Description                                                                                                                                                           |
|-----------------------------|------|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Output                      | `-o` | `./output`         | The output path. The directory will be created if it does not exist.                                                                                                  |
| Aspect Ratio                | `-r` | `4:3`              | The aspect ratio of the resulting images. This depends on the type of slides you are scanning.                                                                        |
| Export Differences          | `-d` | `None` (no export) | Export a differences file for analysis in spreadsheet programs, which is useful for tuning the other parameters.                                                      |
| Capture Threshold           | `-c` | `2`                | How similar the frames need to be before saving the frame. Too low and you may miss slides, too high and you may capture before the exposure has fully adjusted.      |
| Priming Threshold           | `-p` | `50`               | How different the frame needs to be before the capture is primed. Too low and you may capture duplicates, too high and you may miss slides.                           |
| Frames Required for Capture | `-f` | `5`                | How many similar frames in a row are required before capturing. Too low and you may capture before the exposure has fully adjusted, too high and you may miss slides. |
| Start Frame                 | `-s` | `0`                | The frame number processing starts at.                                                                                                                                |
| End Frame                   | `-e` | `None` (no limit)  | The frame number processing ends at.                                                                                                                                  |

### Tips

1. Start by exporting differences (`python slide_to_photo.py <INPUT_PATH> -d differences.csv`) and graphing the result.
    - The priming threshold should be just under the height of the smallest spike.
    - The capture threshold should be just above the height of the largest plateau.
    - ![Example Graph](./example%20graph.jpg)
2. Start the frames required for capture low to ensure all frames all captured, and raise the value as high as possible
   before frames are skipped to ensure the best frame is captured.
