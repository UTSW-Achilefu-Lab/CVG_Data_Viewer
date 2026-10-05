# viewData.py — Updated with GUI Folder Selector (Tkinter)
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# GUI Folder Selector imports
import tkinter as tk
from tkinter import filedialog

try:
    import pydicom
    PYDICOM_AVAILABLE = True
except ImportError:
    PYDICOM_AVAILABLE = False
    print("Warning: pydicom not installed. Run 'pip install pydicom' to enable DCM rendering.")


def select_folder_gui():
    """Opens a native GUI window allowing the user to select an images folder."""
    root = tk.Tk()
    root.withdraw()  # Hide the main Tkinter window
    root.attributes('-topmost', True)  # Bring file picker dialog to the front

    folder_selected = filedialog.askdirectory(
        title="Select Folder Containing Snapshot Images"
    )
    
    root.destroy()
    return folder_selected if folder_selected else None


def unpack_brcm(file_path):
    """Unpacks IMX219 10-bit raw Bayer data into a 16-bit NumPy array."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        raw_bytes = 2480 * 4128
        data = data[32768 : 32768 + raw_bytes]
        data = np.frombuffer(data, dtype=np.uint8)

        reshape, crop = ((2480, 4128), (2464, 4100))
        data = data.reshape(reshape)[:crop[0], :crop[1]]

        data = data.astype(np.uint16) << 2
        for byte in range(4):
            data[:, byte::5] |= ((data[:, 4::5] >> ((4 - byte) * 2)) & 0b11)
        data = np.delete(data, np.s_[4::5], 1)

        return data
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def load_dcm_data(file_path):
    """Reads a DICOM file and returns pixel data array."""
    if not PYDICOM_AVAILABLE or not os.path.exists(file_path):
        return None
    try:
        ds = pydicom.dcmread(file_path)
        if hasattr(ds, 'pixel_array'):
            return ds.pixel_array
    except Exception as e:
        print(f"Failed to read DICOM {file_path}: {e}")
    return None


def group_snapshots(directory):
    """Parses folder and subfolders to group BRCM and DCM files by sequence number."""
    abs_dir = os.path.abspath(directory)

    file_paths = []
    for root, _, files in os.walk(abs_dir):
        for f in files:
            if f.startswith("Snap_") and (f.lower().endswith('.brcm') or f.lower().endswith('.dcm')):
                file_paths.append(os.path.join(root, f))

    sequences = {}
    for full_path in file_paths:
        f = os.path.basename(full_path)
        name_without_ext, ext = os.path.splitext(f)
        ext = ext.lstrip('.').lower()
        parts = name_without_ext.split('_')

        # Split format: Snap_TIMESTAMP_CAV_STATE_SEQ_CAMTYPE
        if len(parts) >= 6:
            state = parts[3]     # LasOn or LasOff
            seq_num = parts[4]   # Sequence number
            cam_type = parts[5]  # 0IMPROC, 0RAW, 1RAW, COMPRAW

            if seq_num not in sequences:
                sequences[seq_num] = {}

            slot_key = f"{state}_{cam_type}_{ext}"
            sequences[seq_num][slot_key] = full_path

    def sort_key(item):
        key = item[0]
        return int(key) if key.isdigit() else key

    return sorted(sequences.items(), key=sort_key)


class SnapshotDCMViewer:
    def __init__(self, sequences):
        self.sequences = sequences
        self.current_idx = 0
        self.show_dcm = False

        self.fig, self.axes = plt.subplots(2, 4, figsize=(18, 9))
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        self.update_display()

    def update_display(self):
        seq_num, slots = self.sequences[self.current_idx]

        mode_str = "DICOM (.dcm)" if self.show_dcm else "Raw Bayer (.brcm)"
        self.fig.suptitle(
            f"Snapshot Sequence #{seq_num} ({self.current_idx + 1}/{len(self.sequences)}) — Viewing: {mode_str}\n"
                f"[ LEFT / RIGHT Arrow: Cycle Sequences | Press 'D': Toggle BRCM / DCM | Press 'Q' : To exit viewer]",
            fontsize=12, fontweight='bold'
        )

        # 7-Slot layout mapping
        layout = [
            (0, 0, 'LasOn_0IMPROC',  'Processed Infrared Frame Cam0', False),
            (0, 1, 'LasOn_0RAW',     'Laser ON - Infrared Frame Cam0 [RAW]', False),
            (0, 2, 'LasOn_1RAW',     'Laser ON - Visible Frame Cam1 [RAW]', False),
            (0, 3, 'LasOn_COMPRAW',  'Laser ON - Composite Overlay Frames VIS | IR', True),  # Always DCM
            (1, 0, 'LasOff_0IMPROC', 'Laser OFF - Infrared Frame Cam0', False),
            (1, 1, 'LasOff_0RAW',    'Laser OFF - Infrared Frame Cam0 [RAW]', False),
            (1, 2, 'LasOff_1RAW',    'Laser OFF - Visible Frame Cam1 [RAW]', False),
        ]

        # Reset all 8 axes
        for r in range(2):
            for c in range(4):
                self.axes[r, c].clear()
                self.axes[r, c].axis('off')

        # Populate defined 7 slots
        for row, col, base_key, label, always_dcm in layout:
            ax = self.axes[row, col]
            
            # If slot is COMPRAW, override target_ext to 'dcm'
            target_ext = 'dcm' if (self.show_dcm or always_dcm) else 'brcm'
            key = f"{base_key}_{target_ext}"

            if key in slots:
                file_path = slots[key]

                if target_ext == 'brcm':
                    img_data = unpack_brcm(file_path)
                    if img_data is not None:
                        ax.imshow(img_data, cmap='gray', vmin=0, vmax=1023)
                else:
                    img_data = load_dcm_data(file_path)
                    if img_data is not None:
                        ax.imshow(img_data, cmap='gray')
                    else:
                        ax.text(0.5, 0.5, "DICOM File Found\n(No Image Array)",
                                ha='center', va='center', transform=ax.transAxes)

                ax.set_title(f"{label}\n{os.path.basename(file_path)}", fontsize=10)
            else:
                ax.set_title(f"{label}\n[{target_ext.upper()} Missing]", fontsize=10, color='red')

        # Hide the unused 8th subplot (bottom-right)
        self.axes[1, 3].set_visible(False)

        self.fig.tight_layout()
        self.fig.canvas.draw()

    def on_key(self, event):
        if event.key == 'right':
            if self.current_idx < len(self.sequences) - 1:
                self.current_idx += 1
                self.update_display()
        elif event.key == 'left':
            if self.current_idx > 0:
                self.current_idx -= 1
                self.update_display()
        elif event.key.lower() == 'd':
            self.show_dcm = not self.show_dcm
            self.update_display()


def main():
    # 1. Use command-line path if provided
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    # 2. Otherwise, prompt user with GUI Folder Picker
    else:
        target_dir = select_folder_gui()

    # Exit if user cancels folder selection dialog
    if not target_dir:
        print("No directory selected. Exiting.")
        return

    print("Checking path:", target_dir)
    sequences = group_snapshots(target_dir)

    if not sequences:
        print(f"No snapshot sequences found in '{os.path.abspath(target_dir)}'")
        return

    print(f"Successfully loaded {len(sequences)} sequence(s). Opening viewer...")
    viewer = SnapshotDCMViewer(sequences)
    plt.show()


if __name__ == "__main__":
    main()

