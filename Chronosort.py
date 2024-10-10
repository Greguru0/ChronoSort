import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel
import os
import hashlib
from datetime import datetime
from PIL import Image, ImageTk
import exifread
import shutil  # Used for efficient file copying


class ChronoSortGUI:
    def __init__(self, main):
        self.root = main
        self.root.title("ChronoSort")
        self.root.resizable(False, False)  # Prevent window resizing

        # Initialize variables
        self.cancel_requested = False
        self.selected_extensions = []
        self.hash_map = {}

        # Set up the GUI components
        self.setup_gui()

    def setup_gui(self):
        # Source Folder
        ttk.Label(self.root, text="Source Folder:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.source_var = tk.StringVar()
        ttk.Entry(self.root, textvariable=self.source_var, width=50).grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(self.root, text="Browse", command=self.browse_source).grid(row=0, column=2, padx=10, pady=5)

        # Destination Folder
        ttk.Label(self.root, text="Destination Folder:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.destination_var = tk.StringVar()
        ttk.Entry(self.root, textvariable=self.destination_var, width=50).grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(self.root, text="Browse", command=self.browse_destination).grid(row=1, column=2, padx=10, pady=5)

        # Folder Structure Options
        folder_frame = ttk.LabelFrame(self.root, text="Folder Structure")
        folder_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky='w')
        self.folder_structure_var = tk.StringVar(value="flat")
        ttk.Radiobutton(folder_frame, text="Flat (YYYY-MM)", variable=self.folder_structure_var, value="flat").grid(row=0, column=0, padx=5, pady=5)
        ttk.Radiobutton(folder_frame, text="Nested (YYYY/MM)", variable=self.folder_structure_var, value="nested").grid(row=0, column=1, padx=5, pady=5)

        # File Extensions
        ext_frame = ttk.LabelFrame(self.root, text="File Extensions")
        ext_frame.grid(row=0, column=3, rowspan=3, padx=10, pady=5, sticky='ns')
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
        for idx, (ext, var) in enumerate(self.extensions.items()):
            ttk.Checkbutton(ext_frame, text=ext, variable=var).grid(row=idx, column=0, sticky='w')

        # Custom Extensions
        ttk.Label(ext_frame, text="Custom Extensions (space-separated):").grid(row=len(self.extensions), column=0, padx=5, pady=(10, 0), sticky='w')
        self.custom_ext_var = tk.StringVar()
        ttk.Entry(ext_frame, textvariable=self.custom_ext_var, width=20).grid(row=len(self.extensions)+1, column=0, padx=5, pady=5)

        # Options
        options_frame = ttk.Frame(self.root)
        options_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=5, sticky='w')
        self.check_duplicates_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Check Duplicates", variable=self.check_duplicates_var).grid(row=0, column=0, padx=5, pady=5)
        self.display_thumbnail_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Display Thumbnails", variable=self.display_thumbnail_var).grid(row=0, column=1, padx=5, pady=5)

        # Start Button
        self.start_button = ttk.Button(self.root, text="START", command=self.start_processing)
        self.start_button.grid(row=4, column=0, padx=10, pady=10, sticky='w')

        # Output Text Box
        self.output_text = tk.Text(self.root, height=10, width=80, state='disabled')
        self.output_text.grid(row=5, column=0, columnspan=4, padx=10, pady=10)

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

        # Open processing window
        self.open_process_window()

        # Start processing after UI updates
        self.root.after(100, self.process_files)

    def open_process_window(self):
        """Opens a new window to display processing progress."""
        self.process_window = Toplevel(self.root)
        self.process_window.title("Processing")
        self.process_window.resizable(False, False)
        self.process_window.protocol("WM_DELETE_WINDOW", self.request_cancel)

        # Output Box
        self.process_output = tk.Text(self.process_window, height=20, width=80, state='disabled')
        self.process_output.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Thumbnail
        self.thumbnail_label = tk.Label(self.process_window)
        self.thumbnail_label.grid(row=0, column=2, padx=10, pady=10)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.process_window, orient="horizontal", length=400, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=0, columnspan=2, padx=10, pady=5)

        # Progress Label
        self.progress_label = ttk.Label(self.process_window, text="0%")
        self.progress_label.grid(row=2, column=2, padx=10, pady=5)

        # Status Label
        self.status_label = ttk.Label(self.process_window, text="Initializing...")
        self.status_label.grid(row=1, column=0, columnspan=3, padx=10, pady=5)

        # Cancel Button
        ttk.Button(self.process_window, text="Cancel", command=self.request_cancel).grid(row=3, column=2, padx=10, pady=10)

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

    def process_files(self):
        """Processes the files based on user inputs."""
        source = self.source_var.get()
        destination = self.destination_var.get()

        # Gather all files to process
        files_to_process = []
        for root_dir, _, files in os.walk(source):
            for file in files:
                ext = os.path.splitext(file)[1][1:].lower()
                if ext in self.selected_extensions:
                    files_to_process.append(os.path.join(root_dir, file))

        total_files = len(files_to_process)
        if total_files == 0:
            messagebox.showinfo("Info", "No files found with the selected extensions.")
            self.start_button.config(text="START", state="normal")
            self.process_window.destroy()
            return

        processed_files = 0
        duplicate_files = 0
        error_files = 0
        duplicate_list = []  # List to keep track of duplicates

        # Hash existing files if checking for duplicates
        if self.check_duplicates:
            self.create_hash_map(destination)
        else:
            self.hash_map = {}

        # Reset progress bar for processing files
        self.progress_var.set(0)
        self.progress_bar['maximum'] = total_files
        self.status_label.config(text="Processing files...")

        for idx, file_path in enumerate(files_to_process, 1):
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
                    date_taken = self.get_date_taken(file_path)
                    if self.folder_structure_var.get() == "nested":
                        dest_folder = os.path.join(destination, date_taken.strftime('%Y'), date_taken.strftime('%m'))
                    else:
                        dest_folder = os.path.join(destination, date_taken.strftime('%Y-%m'))

                    if not os.path.exists(dest_folder):
                        os.makedirs(dest_folder)

                    base_name = date_taken.strftime('%Y-%m-%d')
                    ext = os.path.splitext(file_path)[1].lower()
                    dest_file = os.path.join(dest_folder, base_name + ext)

                    # Handle file name conflicts
                    counter = 1
                    while os.path.exists(dest_file):
                        dest_file = os.path.join(dest_folder, f"{base_name}({counter}){ext}")
                        counter += 1

                    # Copy file
                    shutil.copy2(file_path, dest_file)
                    processed_files += 1
                    self.log_process_output(f"Copied: {file_path} -> {dest_file}")

                    # Display thumbnail
                    if self.display_thumbnail_var.get():
                        self.display_thumbnail(file_path)

            except Exception as e:
                error_files += 1
                self.log_process_output(f"Error processing {file_path}: {e}")

            # Update progress
            self.progress_var.set(idx)
            progress_percent = (idx / total_files) * 100
            self.progress_label.config(text=f"{int(progress_percent)}%")
            self.process_window.update()

        # Finalize
        self.finish_processing(processed_files, total_files, duplicate_files, error_files, duplicate_list)

    def create_hash_map(self, directory):
        """Creates a hash map of existing files in the destination to check for duplicates."""
        self.log_process_output("Creating hash map of existing files...")
        self.status_label.config(text="Hashing existing files...")
        self.process_window.update()

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
        self.progress_bar['maximum'] = total_hash_files

        self.hash_map = {}
        for idx, file_path in enumerate(files_to_hash, 1):
            if self.cancel_requested:
                self.log_output("Hashing cancelled by user.")
                break

            file_hash = self.compute_file_hash(file_path)
            self.hash_map[file_hash] = file_path

            # Update progress
            self.progress_var.set(idx)
            progress_percent = (idx / total_hash_files) * 100
            self.progress_label.config(text=f"{int(progress_percent)}%")
            self.status_label.config(text=f"Hashing existing files... {int(progress_percent)}%")
            self.process_window.update()

        self.log_process_output("Hash map creation complete.")
        self.status_label.config(text="Hashing complete.")
        self.progress_var.set(0)
        self.progress_bar['maximum'] = 100
        self.progress_label.config(text="0%")

    def compute_file_hash(self, file_path):
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
                    return datetime.strptime(str(date_taken), '%Y:%m:%d %H:%M:%S')
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
        duplicates_window = Toplevel(self.root)
        duplicates_window.title("Duplicate Files Skipped")
        duplicates_window.resizable(False, False)

        # Text Box for duplicates
        duplicates_text = tk.Text(duplicates_window, height=20, width=80)
        duplicates_text.pack(padx=10, pady=10)

        duplicates_text.insert(tk.END, "List of duplicate files skipped:\n\n")
        for info in duplicate_list:
            duplicates_text.insert(tk.END, info + "\n\n")
        duplicates_text.config(state='disabled')

        # Close Button
        ttk.Button(duplicates_window, text="Close", command=duplicates_window.destroy).pack(pady=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = ChronoSortGUI(root)
    root.mainloop()
