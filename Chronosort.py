import os
import threading
import hashlib
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import re

# External libraries
try:
    from PIL import Image, ImageTk
except ImportError:
    messagebox.showerror("Missing Dependency", "Please install Pillow library:\npip install Pillow")
    exit()

try:
    import exifread
except ImportError:
    messagebox.showerror("Missing Dependency", "Please install exifread library:\npip install exifread")
    exit()

# Use ttkbootstrap for modern styling
try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
except ImportError:
    messagebox.showerror("Missing Dependency", "Please install ttkbootstrap library:\npip install ttkbootstrap")
    exit()


class ChronoSortGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ChronoSort")
        self.root.resizable(False, False)

        # Initialize variables
        self.cancel_requested = False
        self.selected_extensions = []
        self.hash_map = {}
        self.folder_max_numbers = {}  # Add this line to initialize the dictionary
        self.processing_thread = None

        # Set up the GUI components
        self.setup_gui()


    def setup_gui(self):
        # Main Frame
        main_frame = ttkb.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # Source Folder
        source_frame = ttkb.Frame(main_frame)
        source_frame.pack(fill=X, pady=5)
        ttkb.Label(source_frame, text="Source Folder:").pack(side=LEFT, padx=5)
        self.source_var = tk.StringVar()
        ttkb.Entry(source_frame, textvariable=self.source_var, width=50).pack(side=LEFT, padx=5)
        ttkb.Button(source_frame, text="Browse", command=self.browse_source).pack(side=LEFT, padx=5)

        # Destination Folder
        dest_frame = ttkb.Frame(main_frame)
        dest_frame.pack(fill=X, pady=5)
        ttkb.Label(dest_frame, text="Destination Folder:").pack(side=LEFT, padx=5)
        self.destination_var = tk.StringVar()
        ttkb.Entry(dest_frame, textvariable=self.destination_var, width=50).pack(side=LEFT, padx=5)
        ttkb.Button(dest_frame, text="Browse", command=self.browse_destination).pack(side=LEFT, padx=5)

        # Folder Structure Options
        folder_frame = ttkb.LabelFrame(main_frame, text="Folder Structure")
        folder_frame.pack(fill=X, pady=5)
        self.folder_structure_var = tk.StringVar(value="flat")
        ttkb.Radiobutton(folder_frame, text="Flat (YYYY-MM)", variable=self.folder_structure_var,
                         value="flat").pack(side=LEFT, padx=5)
        ttkb.Radiobutton(folder_frame, text="Nested (YYYY/MM)", variable=self.folder_structure_var,
                         value="nested").pack(side=LEFT, padx=5)

        # File Extensions
        ext_frame = ttkb.LabelFrame(main_frame, text="File Extensions")
        ext_frame.pack(fill=X, pady=5)
        self.extensions = {
            "JPEG": tk.BooleanVar(value=True),
            "JPG": tk.BooleanVar(value=True),
            "PNG": tk.BooleanVar(value=True),
            "GIF": tk.BooleanVar(),
            "BMP": tk.BooleanVar(),
            "TIFF": tk.BooleanVar(),
            "RAW": tk.BooleanVar(),
            "ARW": tk.BooleanVar(),
            "CR2": tk.BooleanVar(),
            "NEF": tk.BooleanVar(),
            "ORF": tk.BooleanVar()
        }
        ext_inner_frame = ttkb.Frame(ext_frame)
        ext_inner_frame.pack()
        for idx, (ext, var) in enumerate(self.extensions.items()):
            ttkb.Checkbutton(ext_inner_frame, text=ext, variable=var).grid(row=idx // 4, column=idx % 4, sticky='w')

        # Custom Extensions
        custom_ext_frame = ttkb.Frame(main_frame)
        custom_ext_frame.pack(fill=X, pady=5)
        ttkb.Label(custom_ext_frame, text="Custom Extensions (space-separated):").pack(side=LEFT, padx=5)
        self.custom_ext_var = tk.StringVar()
        ttkb.Entry(custom_ext_frame, textvariable=self.custom_ext_var, width=30).pack(side=LEFT, padx=5)

        # Options
        options_frame = ttkb.Frame(main_frame)
        options_frame.pack(fill=X, pady=5)
        
        self.check_duplicates_var = tk.BooleanVar()
        ttkb.Checkbutton(options_frame, text="Check Duplicates", variable=self.check_duplicates_var).pack(side=LEFT, padx=5)
        
        self.display_thumbnail_var = tk.BooleanVar()
        ttkb.Checkbutton(options_frame, text="Display Thumbnails", variable=self.display_thumbnail_var).pack(side=LEFT, padx=5)
        
        self.rename_existing_var = tk.BooleanVar()
        ttkb.Checkbutton(options_frame, text="Rename existing photos in destination", variable=self.rename_existing_var).pack(side=LEFT, padx=5)

        # Start Button
        self.start_button = ttkb.Button(main_frame, text="START", command=self.start_processing, bootstyle=SUCCESS)
        self.start_button.pack(pady=10)

        # Output Text Box
        self.output_text = tk.Text(main_frame, height=10, state='disabled')
        self.output_text.pack(fill=BOTH, expand=True)

    def browse_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_var.set(folder)

    def browse_destination(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination_var.set(folder)

    def log_output(self, message):
        """Logs messages to the main output text box."""
        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, message + '\n')
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')

    def validate_paths(self):
        """Validates that the source and destination paths are valid directories."""
        source = self.source_var.get()
        destination = self.destination_var.get()
        if not os.path.isdir(source):
            messagebox.showerror("Error", "The source folder does not exist.")
            return False
        if not os.path.isdir(destination):
            messagebox.showerror("Error", "The destination folder does not exist.")
            return False
        return True

    def start_processing(self):
        """Starts the file processing."""
        if not self.validate_paths():
            return

        self.start_button.config(text="Running...", state="disabled")
        self.cancel_requested = False

        # Reset folder max numbers cache
        self.folder_max_numbers = {}

        # Get selected extensions
        self.selected_extensions = [ext.lower() for ext, var in self.extensions.items() if var.get()]
        custom_extensions = self.custom_ext_var.get().split()
        if custom_extensions:
            self.selected_extensions.extend([ext.lower() for ext in custom_extensions])

        if not self.selected_extensions:
            messagebox.showerror("Error", "Please select at least one file extension.")
            self.start_button.config(text="START", state="normal")
            return

        self.check_duplicates = self.check_duplicates_var.get()
        self.rename_existing = self.rename_existing_var.get()  # Retrieve the value

        # Open processing window
        self.open_process_window()

        # Start processing in a new thread
        self.processing_thread = threading.Thread(target=self.process_files)
        self.processing_thread.start()



    def rename_existing_photos(self, destination):
        """Renames existing photos in the destination folder (non-recursively) if they don't fit the naming scheme."""
        self.log_process_output(f"Renaming existing photos in destination folder: {destination}")
        self.status_label.config(text="Renaming existing photos...")
        self.process_window.update_idletasks()

        # Initialize used_numbers set and max_existing_number
        used_numbers = set()
        max_existing_number = 0

        # Lists to store files that match and don't match the naming scheme
        files_to_rename = []
        pattern = r'^(\d{4}-\d{2}-\d{2})\((\d+)\)(\.[^.]+)$'  # Adjusted to capture date, number, and extension

        # First pass: collect used numbers and files to rename
        files_in_destination = os.listdir(destination)
        total_files = len(files_in_destination)
        if total_files == 0:
            self.log_process_output("No files found in the destination folder to rename.")
            return

        for file_name in files_in_destination:
            file_path = os.path.join(destination, file_name)
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_name)[1].lower()
                if ext[1:] in self.selected_extensions:
                    match = re.match(pattern, file_name)
                    if match:
                        # File matches naming scheme
                        number = int(match.group(2))
                        used_numbers.add(number)
                        if number > max_existing_number:
                            max_existing_number = number
                        # No need to rename
                        self.log_process_output(f"File already matches naming scheme: {file_name}")
                    else:
                        # File does not match naming scheme; collect for renaming
                        date_taken = self.get_date_taken(file_path)
                        files_to_rename.append((file_name, file_path, date_taken))
        
        # Sort files to rename by date taken
        files_to_rename.sort(key=lambda x: x[2])

        # Second pass: rename files that don't match the naming scheme
        next_number = 1
        for idx, (file_name, file_path, date_taken) in enumerate(files_to_rename, 1):
            if self.cancel_requested:
                self.log_output("Renaming cancelled by user.")
                break

            # Find the next available number not in used_numbers
            while next_number in used_numbers:
                next_number += 1

            try:
                base_name = date_taken.strftime('%Y-%m-%d')
                ext = os.path.splitext(file_name)[1].lower()
                new_file_name = f"{base_name}({next_number}){ext}"
                new_file_path = os.path.join(destination, new_file_name)

                # Rename the file
                os.rename(file_path, new_file_path)
                self.log_process_output(f"Renamed: {file_name} -> {new_file_name}")

                # Update used_numbers and max_existing_number
                used_numbers.add(next_number)
                if next_number > max_existing_number:
                    max_existing_number = next_number

                next_number += 1

            except Exception as e:
                self.log_process_output(f"Error renaming {file_name}: {e}")

            # Update progress
            progress_percent = (idx / len(files_to_rename)) * 100
            self.progress_var.set(progress_percent)
            self.status_label.config(
                text=f"Renaming existing photos... ({idx}/{len(files_to_rename)} - {int(progress_percent)}%)"
            )
            self.process_window.update_idletasks()

        # Update the folder's max number after renaming
        self.folder_max_numbers[destination] = max_existing_number

        self.log_process_output("Renaming existing photos complete.")
        self.status_label.config(text="Renaming complete.")
        self.progress_var.set(0)



    def open_process_window(self):
        """Opens a new window to display processing progress."""
        self.process_window = ttkb.Toplevel(self.root)
        self.process_window.title("Processing")
        self.process_window.resizable(False, False)
        self.process_window.protocol("WM_DELETE_WINDOW", self.request_cancel)

        # Output Box
        self.process_output = tk.Text(self.process_window, height=15, state='disabled')
        self.process_output.pack(fill=BOTH, padx=10, pady=10)

        # Thumbnail
        self.thumbnail_label = ttkb.Label(self.process_window)
        self.thumbnail_label.pack(pady=5)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttkb.Progressbar(self.process_window, orient="horizontal", length=400,
                                             variable=self.progress_var, maximum=100)
        self.progress_bar.pack(pady=5)

        # Status Label
        self.status_label = ttkb.Label(self.process_window, text="Initializing...")
        self.status_label.pack()

        # Cancel Button
        ttkb.Button(self.process_window, text="Cancel", command=self.request_cancel, bootstyle=DANGER).pack(pady=10)

    def log_process_output(self, message):
        """Logs messages to the processing window's output box."""
        self.process_output.config(state='normal')
        self.process_output.insert(tk.END, message + '\n')
        self.process_output.see(tk.END)
        self.process_output.config(state='disabled')

    def request_cancel(self):
        """Sets the flag to cancel processing."""
        self.cancel_requested = True
        self.log_output("Cancelling process...")

    def initialize_folder_max_number(self, folder, ext):
        """Initializes or updates the highest number already used in the destination folder."""
        if folder not in self.folder_max_numbers:
            # If the folder hasn't been processed yet, scan for the max number
            used_numbers = set()
            max_number = 0
            pattern = r'^\d{4}-\d{2}-\d{2}\((\d+)\)' + re.escape(ext) + r'$'
            if os.path.exists(folder):
                for file_name in os.listdir(folder):
                    if file_name.endswith(ext):
                        match = re.match(pattern, file_name)
                        if match:
                            number = int(match.group(1))
                            used_numbers.add(number)
                            if number > max_number:
                                max_number = number
            self.folder_max_numbers[folder] = max_number
        else:
            max_number = self.folder_max_numbers[folder]

        # Return the next available number
        return max_number + 1





    def process_files(self):
        """Processes the files based on user inputs."""
        source = self.source_var.get()
        destination = self.destination_var.get()

        # Reset folder max numbers cache at the beginning of processing
        self.folder_max_numbers = {}

        try:
            # Gather all files to process
            all_files = []
            for root_dir, _, files in os.walk(source):
                for file in files:
                    ext = os.path.splitext(file)[1][1:].lower()
                    if ext in self.selected_extensions:
                        all_files.append(os.path.join(root_dir, file))

            total_files = len(all_files)
            if total_files == 0:
                messagebox.showinfo("Info", "No files found with the selected extensions.")
                self.start_button.config(text="START", state="normal")
                self.process_window.destroy()
                return

            # Read EXIF data and gather files with dates
            files_with_dates = []
            self.status_label.config(text="Reading EXIF data...")
            for idx, file_path in enumerate(all_files, 1):
                date_taken = self.get_date_taken(file_path)
                files_with_dates.append((file_path, date_taken))

                # Update progress
                progress_percent = (idx / total_files) * 100
                self.progress_var.set(progress_percent)
                self.status_label.config(
                    text=f"Reading EXIF data... ({idx}/{total_files} - {int(progress_percent)}%)"
                )
                self.process_window.update_idletasks()

            # Sort files by Date Taken
            files_with_dates.sort(key=lambda x: x[1])

            # Gather destination folders
            dest_folders = set()
            for file_path, date_taken in files_with_dates:
                if self.folder_structure_var.get() == "nested":
                    dest_folder = os.path.join(
                        destination, date_taken.strftime('%Y'), date_taken.strftime('%m')
                    )
                else:
                    dest_folder = os.path.join(destination, date_taken.strftime('%Y-%m'))
                dest_folders.add(dest_folder)

            # Create the folders if they do not exist
            for dest_folder in dest_folders:
                if not os.path.exists(dest_folder):
                    os.makedirs(dest_folder)

            # If renaming existing photos is requested
            if self.rename_existing:
                for dest_folder in dest_folders:
                    self.rename_existing_photos(dest_folder)

            # Reset progress bar for processing
            self.progress_var.set(0)
            self.status_label.config(text="Processing files...")

            processed_files = 0
            duplicate_files = 0
            error_files = 0
            duplicate_list = []

            # Hash existing files if checking for duplicates
            if self.check_duplicates:
                self.create_hash_map(destination)
            else:
                self.hash_map = {}

            for idx, (file_path, date_taken) in enumerate(files_with_dates, 1):
                if self.cancel_requested:
                    self.log_output("Process cancelled by user.")
                    break

                try:
                    is_duplicate = False
                    if self.check_duplicates:
                        duplicate_path = self.is_duplicate(file_path)
                        if duplicate_path:
                            duplicate_files += 1
                            is_duplicate = True
                            duplicate_info = f"Duplicate skipped: {file_path}\nOriginal file: {duplicate_path}"
                            duplicate_list.append(duplicate_info)
                            self.log_process_output(duplicate_info)

                    if not is_duplicate:
                        # Determine destination path
                        if self.folder_structure_var.get() == "nested":
                            dest_folder = os.path.join(
                                destination, date_taken.strftime('%Y'), date_taken.strftime('%m')
                            )
                        else:
                            dest_folder = os.path.join(destination, date_taken.strftime('%Y-%m'))

                        base_name = date_taken.strftime('%Y-%m-%d')
                        ext = os.path.splitext(file_path)[1].lower()

                        # Initialize or retrieve the next available number for this folder
                        next_number = self.initialize_folder_max_number(dest_folder, ext)

                        # Create the destination file path with the new sequential number
                        dest_file = os.path.join(dest_folder, f"{base_name}({next_number}){ext}")

                        # Copy the file to the destination
                        shutil.copy2(file_path, dest_file)
                        processed_files += 1
                        self.log_process_output(f"Copied: {file_path} -> {dest_file}")

                        # Display thumbnail if enabled
                        if self.display_thumbnail_var.get():
                            self.display_thumbnail(file_path)

                        # Update the folder's max number to reflect the newly added file
                        self.folder_max_numbers[dest_folder] = next_number

                    # Update progress
                    progress_percent = (idx / total_files) * 100
                    self.progress_var.set(progress_percent)
                    self.status_label.config(
                        text=f"Processing files... ({idx}/{total_files} - {int(progress_percent)}%)"
                    )
                    self.process_window.update_idletasks()

                except Exception as e:
                    error_files += 1
                    self.log_process_output(f"Error processing {file_path}: {e}")

            # Finalize
            self.finish_processing(
                processed_files, total_files, duplicate_files, error_files, duplicate_list
            )

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during processing: {e}")
            self.start_button.config(text="START", state="normal")
            self.process_window.destroy()







    def create_hash_map(self, directory):
        """Creates a hash map of existing files in the destination to check for duplicates."""
        self.log_process_output("Creating hash map of existing files...")
        self.status_label.config(text="Hashing existing files...")
        self.process_window.update_idletasks()

        # Gather all files to hash
        files_to_hash = []
        for root_dir, _, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1][1:].lower()
                if ext in self.selected_extensions:
                    files_to_hash.append(os.path.join(root_dir, file))

        total_hash_files = len(files_to_hash)
        if total_hash_files == 0:
            self.log_process_output("No existing files to hash.")
            return

        self.progress_var.set(0)
        for idx, file_path in enumerate(files_to_hash, 1):
            if self.cancel_requested:
                self.log_output("Hashing cancelled by user.")
                break

            file_hash = self.compute_file_hash(file_path)
            self.hash_map[file_hash] = file_path

            # Update progress
            progress_percent = (idx / total_hash_files) * 100
            self.progress_var.set(progress_percent)
            self.status_label.config(
                text=f"Hashing existing files... ({idx}/{total_hash_files} - {int(progress_percent)}%)"
            )
            self.process_window.update_idletasks()

        self.log_process_output("Hash map creation complete.")
        self.status_label.config(text="Hashing complete.")
        self.progress_var.set(0)


    @staticmethod
    def compute_file_hash(file_path):
        """Computes the MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):  # Read in 8KB chunks
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def is_duplicate(self, file_path):
        """Checks if a file is a duplicate based on its hash."""
        file_hash = self.compute_file_hash(file_path)
        return self.hash_map.get(file_hash)

    def get_date_taken(self, file_path):
        """Extracts the date taken from EXIF data or falls back to file's modified date."""
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal")
                date_taken = tags.get("EXIF DateTimeOriginal")
                if date_taken:
                    # Handle potential variations in date format
                    date_str = str(date_taken)
                    for fmt in ('%Y:%m:%d %H:%M:%S', '%Y:%m:%d %H:%M:%S%z'):
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
        except Exception as e:
            self.log_process_output(f"Error reading EXIF data for {file_path}: {e}")
        # Fallback to last modified date
        return datetime.fromtimestamp(os.path.getmtime(file_path))


    def display_thumbnail(self, file_path):
        """Displays a thumbnail of the current image."""
        try:
            image = Image.open(file_path)
            image.thumbnail((200, 200))
            photo = ImageTk.PhotoImage(image)
            self.thumbnail_label.config(image=photo)
            self.thumbnail_label.image = photo
        except Exception as e:
            self.log_process_output(f"Error displaying thumbnail for {file_path}: {e}")

    def finish_processing(self, processed_files, total_files, duplicate_files, error_files, duplicate_list):
        """Handles the completion of the file processing."""
        self.log_output(f"Processing complete: {processed_files}/{total_files} files copied.")
        if self.check_duplicates and duplicate_files > 0:
            self.log_output(f"Duplicates skipped: {duplicate_files}")
            self.show_duplicate_window(duplicate_list)
        if error_files > 0:
            self.log_output(f"Errors occurred: {error_files} files failed to process.")
        self.start_button.config(text="START", state="normal")
        self.process_window.destroy()

    def show_duplicate_window(self, duplicate_list):
        """Displays a new window with the list of duplicate files."""
        duplicates_window = ttkb.Toplevel(self.root)
        duplicates_window.title("Duplicate Files Skipped")
        duplicates_window.resizable(False, False)

        # Text Box for duplicates
        duplicates_text = tk.Text(duplicates_window, height=20)
        duplicates_text.pack(fill=BOTH, padx=10, pady=10)

        duplicates_text.insert(tk.END, "List of duplicate files skipped:\n\n")
        for info in duplicate_list:
            duplicates_text.insert(tk.END, info + "\n\n")
        duplicates_text.config(state='disabled')

        # Close Button
        ttkb.Button(duplicates_window, text="Close", command=duplicates_window.destroy).pack(pady=10)


if __name__ == "__main__":
    root = ttkb.Window(themename="superhero")  # Use a modern theme
    app = ChronoSortGUI(root)
    root.mainloop()
