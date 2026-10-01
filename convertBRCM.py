# This script converts the .brcm files in the current directory to 16 bit PNG images.
# Adapted from the Python code in "Raw Bayer data captures" from PiCamera document.
# https://picamera.readthedocs.io/en/release-1.13/recipes2.html#raw-bayer-data-captures

import os
import sys
import numpy as np
import imageio.v3
import tifffile
import matplotlib.pyplot as plt

def convertBRCM(input_file):
    in_file = open(input_file, "rb")
    data = in_file.read()
    in_file.close()
    data = data[32768:]
    data = np.frombuffer(data, dtype=np.uint8)

    # For the V1 module, the data consists of 1952 rows of 3264 bytes of data.
    # The last 8 rows of data are unused (they only exist because the maximum
    # resolution of 1944 rows is rounded up to the nearest 16).
    #
    # For the V2 module, the data consists of 2480 rows of 4128 bytes of data.
    # There's actually 2464 rows of data, but the sensor's raw size is 2466
    # rows, rounded up to the nearest multiple of 16: 2480.
    #
    # Likewise, the last few bytes of each row are unused (why?). Here we
    # reshape the data and strip off the unused bytes.
    reshape, crop = ((2480, 4128), (2464, 4100))

    data = data.reshape(reshape)[:crop[0], :crop[1]]

    # Horizontally, each row consists of 10-bit values. Every four bytes are
    # the high 8-bits of four values, and the 5th byte contains the packed low
    # 2-bits of the preceding four values. In other words, the bits of the
    # values A, B, C, D and arranged like so:
    #
    #  byte 1   byte 2   byte 3   byte 4   byte 5
    # AAAAAAAA BBBBBBBB CCCCCCCC DDDDDDDD AABBCCDD
    #
    # Here, we convert our data into a 16-bit array, shift all values left by
    # 2-bits and unpack the low-order bits from every 5th byte in each row,
    # then remove the columns containing the packed bits

    data = data.astype(np.uint16) << 2
    for byte in range(4):
        data[:, byte::5] |= ((data[:, 4::5] >> ((4 - byte) * 2)) & 0b11)
    data = np.delete(data, np.s_[4::5], 1)

    # Create 'outputTIFF' directory
    output_dir = "convertedTIFFs"
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.basename(input_file).rsplit('.', maxsplit=1)[0] + '.tiff'
    out_file = os.path.join(output_dir, base_name)

    imageio.imwrite(out_file, data)
    print("Success : ", out_file)
    return out_file
    # Output data to 16-bit gray-scale TIFF file.
    # The [0] extracts the original filename w/o it's original extension so we can
    # safely attach a new filename like .tiff
    #out_file = input_file.rsplit('.', maxsplit=1)[0] + '.tiff'
    #imageio.imwrite(out_file, data)
    #print(out_file)
    #return

class ImageGridViewer:
    """Interactive viewer for cycling through 16-bit images in batches of 6."""
    def __init__(self, tiff_files):
        self.tiff_files = tiff_files
        self.page_size = 6
        self.current_page = 0
        self.total_pages = max(1, (len(tiff_files) + self.page_size - 1) // self.page_size)

        self.fig, self.axes = plt.subplots(2, 3, figsize=(15, 9))
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        self.draw_page()

    def draw_page(self):
        start_idx = self.current_page * self.page_size
        batch = self.tiff_files[start_idx : start_idx + self.page_size]

        self.fig.suptitle(
            f"Page {self.current_page + 1}/{self.total_pages} (Use Left/Right Arrow Keys)",
            fontsize=14,
            fontweight='bold'
        )

        for i, ax in enumerate(self.axes.flat):
            ax.clear()
            if i < len(batch):
                file_path = batch[i]
                # Read original 16-bit data intact
                img_data = imageio.v3.imread(file_path)

                # Display with Matplotlib using 10-bit raw ranges (0 - 1023)
                ax.imshow(img_data, cmap='gray', vmin=0, vmax=1023)
                ax.set_title(os.path.basename(file_path), fontsize=8)
            ax.axis('off')

        self.fig.canvas.draw()

    def on_key(self, event):
        if event.key == 'right':
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                self.draw_page()
        elif event.key == 'left':
            if self.current_page > 0:
                self.current_page -= 1
                self.draw_page()

def main():
    convertFiles = input("Do you need to convert the image files (Y/N)?")
    match convertFiles:
        case 'y' | 'Y':
            print("yes")
            res = []
            # Iterate directory
            for file in os.listdir():
                # check only text files
                if file.endswith('.brcm'):
                    res.append(file)
            print(res)

            for brcm_file in res:
                print(brcm_file)
                convertBRCM(brcm_file)
        case 'n' | 'N':
            print("no")

    # Load converted TIFF files for viewing
    tiff_dir = "convertedTIFFs"
    if os.path.exists(tiff_dir):
        tiff_files = sorted([
            os.path.join(tiff_dir, f)
            for f in os.listdir(tiff_dir)
            if f.endswith('.tiff') or f.endswith('.tif')
        ])

        if tiff_files:
            print(f"\nLaunching viewer with {len(tiff_files)} TIFF images...")
            viewer = ImageGridViewer(tiff_files)
            plt.show()
        else:
            print("No .tiff files found in 'convertedTIFFs' directory.")
    else:
        print("Directory 'convertedTIFFs' does not exist.")

if __name__ == "__main__":
    main()
