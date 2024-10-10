# ChronoSort
# This program will transfer files from a SOURCE folder to a DESTINATION folder and check for duplicates with hash values. Will handle renaming. Will rename files to their date taken/modified. Ideal for images, but can be used for any filetype.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel
import os
import hashlib
from datetime import datetime
from PIL import Image, ImageTk
from PIL.ExifTags import TAGS
import exifread  # Single library for handling EXIF data from all supported formats


class ImageSorterGUI:
    def __init__(self, main):
        self.root = main
        self.root.title("ChronoSort")

        # Add this in the __init__ method to create radio buttons for folder structure
        self.folder_structure_frame = ttk.LabelFrame(main, text="Folder Structure")
        self.folder_structure_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky='w')

        # Create a single variable to hold the value for the folder structure
        self.folder_structure_var = tk.StringVar(value="flat")  # Default to "flat"

        # Radio buttons for "Nested" and "Flat" options
        self.flat_rb = ttk.Radiobutton(self.folder_structure_frame, text="Flat Folder (Destination/YYYY-MM/File)", variable=self.folder_structure_var, value="flat")
        self.flat_rb.grid(row=0, column=0, sticky='w')
        
        self.nested_rb = ttk.Radiobutton(self.folder_structure_frame, text="Nested Folder (Destination/YYYY/MM/File)", variable=self.folder_structure_var, value="nested")
        self.nested_rb.grid(row=0, column=1, sticky='w')

        # Add a checkbox to control whether thumbnails should be displayed
        self.display_thumbnail_var = tk.BooleanVar(value=True)  # Default is True (display thumbnails)
        self.thumbnail_cb = ttk.Checkbutton(main, text="Display Thumbnails", variable=self.display_thumbnail_var)
        self.thumbnail_cb.grid(row=4, column=2, sticky='w', padx=10, pady=10)
        
        # Dropdowns for Source and Destination
        self.source_label = ttk.Label(main, text="Source Folder")
        self.source_label.grid(row=0, column=0, padx=10, pady=10)
        self.source_button = ttk.Button(main, text="Browse", command=self.browse_source)
        self.source_button.grid(row=0, column=1, padx=10, pady=10)
        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(main, textvariable=self.source_var, width=50)
        self.source_entry.grid(row=0, column=2, padx=10, pady=10)

        self.destination_label = ttk.Label(main, text="Destination Folder")
        self.destination_label.grid(row=1, column=0, padx=10, pady=10)
        self.destination_button = ttk.Button(main, text="Browse", command=self.browse_destination)
        self.destination_button.grid(row=1, column=1, padx=10, pady=10)
        self.destination_var = tk.StringVar()
        self.destination_entry = ttk.Entry(main, textvariable=self.destination_var, width=50)
        self.destination_entry.grid(row=1, column=2, padx=10, pady=10)

        # Checkboxes for image extensions
        self.extension_frame = ttk.LabelFrame(main, text="File Extensions")
        self.extension_frame.grid(row=0, column=3, rowspan=4, padx=10, pady=10, sticky='n')

        self.extensions = {
            "JPEG": tk.BooleanVar(),
            "JPG": tk.BooleanVar(),
            "PNG": tk.BooleanVar(),
            "GIF": tk.BooleanVar(),
            "BMP": tk.BooleanVar(),
            "TIFF": tk.BooleanVar(),
            "RAW": tk.BooleanVar(),
            "ARW": tk.BooleanVar(),
            "CR2": tk.BooleanVar(),
            "NEF": tk.BooleanVar(),
            "ORF": tk.BooleanVar()
        }

        row = 0
        for ext, var in self.extensions.items():
            cb = ttk.Checkbutton(self.extension_frame, text=ext, variable=var)
            cb.grid(row=row, column=0, sticky='w')
            row += 1

        # Custom extensions entry
        self.custom_ext_var = tk.StringVar()
        self.custom_ext_cb = ttk.Checkbutton(self.extension_frame, text="Custom Extensions", variable=tk.BooleanVar())
        self.custom_ext_cb.grid(row=row, column=0, sticky='w')
        self.custom_ext_entry = ttk.Entry(self.extension_frame, textvariable=self.custom_ext_var, width=20)
        self.custom_ext_entry.grid(row=row + 1, column=0, padx=10, pady=10)

        # Text box for output
        self.output_text = tk.Text(main, height=10, width=80)
        self.output_text.grid(row=5, column=0, columnspan=4, padx=10, pady=10)

        # Start button and Check Duplicates checkbox
        self.check_duplicates_var = tk.BooleanVar()
        self.check_duplicates_cb = ttk.Checkbutton(main, text="Check Duplicates", variable=self.check_duplicates_var)
        self.check_duplicates_cb.grid(row=4, column=1, sticky='w', padx=10, pady=10)

        self.start_button = ttk.Button(main, text="START", command=self.start_scrape)
        self.start_button.grid(row=4, column=0, padx=10, pady=10, sticky='e')
            
    def browse_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_var.set(folder)

    def browse_destination(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination_var.set(folder)

    def validate_paths(self):
        source = self.source_var.get()
        destination = self.destination_var.get()

        if not os.path.isdir(source):
            messagebox.showerror("Error", "The source folder does not exist.")
            return False
        if not os.path.isdir(destination):
            messagebox.showerror("Error", "The destination folder does not exist.")
            return False
        return True

    def start_scrape(self):
        if not self.validate_paths():
            return

        self.start_button.config(text="Running", state="disabled")
        self.output_text.insert(tk.END, f"Process started at {datetime.now().strftime('%m-%d-%Y - %H:%M:%S')}\n")
        self.output_text.see(tk.END)  # Autoscroll

        self.selected_extensions = [ext.lower() for ext, var in self.extensions.items() if var.get()]
        custom_extensions = self.custom_ext_var.get().split()

        if custom_extensions:
            self.selected_extensions.extend([ext.lower() for ext in custom_extensions])

        self.check_duplicates = self.check_duplicates_var.get()

        # Open separate output window
        self.output_window = Toplevel(self.root)
        self.output_window.title("Process Window")
        self.output_window.protocol("WM_DELETE_WINDOW", self.on_output_window_close)

        # Text box for logging
        self.output_box = tk.Text(self.output_window, height=20, width=80)
        self.output_box.grid(row=0, column=0, padx=10, pady=10)

        # Label for displaying the current thumbnail
        self.thumbnail_label = tk.Label(self.output_window)
        self.thumbnail_label.grid(row=0, column=1, padx=10, pady=10)

        # Label for displaying current/total
        self.progress_label = tk.Label(self.output_window, text="0/0")
        self.progress_label.grid(row=1, column=1, padx=10, pady=5)

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.output_window, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.grid(row=2, column=1, padx=10, pady=5)

        self.stop_processing = False  # Flag to stop processing

        # Schedule the hashing process to start after the UI has had time to update
        self.output_window.after(100, self.process_files)

    def create_hash_map(self):
        destination = self.destination_var.get()
        hash_map = {}

        self.output_box.insert(tk.END, "Hashing files...\n")
        self.output_box.see(tk.END)  # Autoscroll
        self.output_window.update()  # Ensure the window updates before starting the hash process

        for root, dirs, files in os.walk(destination):
            for file in files:
                ext = file.split('.')[-1].lower()
                if ext in self.selected_extensions:  # Only hash files with selected extensions
                    dest_path = os.path.join(root, file)
                    file_hash = self.get_file_hash(dest_path)
                    hash_map[file_hash] = dest_path

        self.output_box.insert(tk.END, "Hashing complete.\n")
        self.output_box.see(tk.END)  # Autoscroll

        return hash_map

    def process_files(self):
        if self.check_duplicates:
            self.hash_map = self.create_hash_map()

        source = self.source_var.get()
        destination = self.destination_var.get()
        processed_files = 0
        duplicate_files = 0
        error_files = 0
        list_errors = []
        list_duplicates = []
        total_files = sum([len([file for file in files if file.split('.')[-1].lower() in self.selected_extensions]) for r, d, files in os.walk(source)])

        self.output_text.insert(tk.END, f"Total files to process: {total_files}\n")
        self.output_text.see(tk.END)  # Autoscroll

        current_file = 0  # Track the current file being processed

        for root, dirs, files in os.walk(source):
            for file in files:
                if self.stop_processing:
                    self.output_text.insert(tk.END, "Process cancelled by user.\n")
                    self.output_text.see(tk.END)  # Autoscroll
                    self.finish_process(processed_files, total_files, duplicate_files, list_duplicates)
                    self.output_window.destroy()
                    return

                ext = file.split('.')[-1].lower()
                if ext in self.selected_extensions:
                    current_file += 1  # Increment the current file count
                    src_path = os.path.join(root, file)
                    try:
                        date_taken = self.get_date_taken(src_path)
                        if not date_taken:
                            date_taken = datetime.fromtimestamp(os.path.getmtime(src_path))

                        year = date_taken.strftime('%Y')
                        month = date_taken.strftime('%m')
                        dest_folder = os.path.join(destination, year, month)
                        
                        # Check the value of self.folder_structure_var to determine which folder structure to use
                        if self.folder_structure_var.get() == "nested":
                            dest_folder = os.path.join(destination, year, month)  # Nested folder (Destination/Year/Month)
                        elif self.folder_structure_var.get() == "flat":
                            dest_folder = os.path.join(destination, f"{year}-{month}")  # Flat folder (Destination/Year-Month)
                        else:
                            print("Something went wrong.")
                            exitapp

                        # Create the destination folder if it does not exist
                        if not os.path.exists(dest_folder):
                            os.makedirs(dest_folder)  # This will create the directory, including any intermediate directories

                        file_base_name = date_taken.strftime('%Y-%m-%d')
                        dest_path = os.path.join(dest_folder, f"{file_base_name}(1).{ext}")
                        dest_path = os.path.normpath(dest_path)

                        index = 1
                        while os.path.exists(dest_path):
                            index += 1
                            dest_path = os.path.join(dest_folder, f"{file_base_name}({index}).{ext}")

                        if self.check_duplicates:
                            duplicate_path = self.is_duplicate(src_path)
                            if duplicate_path:
                                duplicate_files += 1
                                list_duplicates.append(f"{src_path} > {duplicate_path} : DUPLICATE")
                                self.output_box.insert(tk.END, f"{src_path} > {duplicate_path} : DUPLICATE\n")
                                self.output_box.see(tk.END)  # Autoscroll
                                continue

                        self.copy_file(src_path, dest_path)
                        processed_files += 1
                        self.output_box.insert(tk.END, f"Copied: {src_path}\n|___{dest_path}\n")
                        self.output_box.see(tk.END)  # Autoscroll
                        if self.display_thumbnail_var.get():
                            self.display_thumbnail(src_path)
                        else:
                            self.output_box.insert(tk.END, "Thumbnail display is disabled.\n")

                        self.progress_label.config(text=f"{current_file}/{total_files}")  # Update progress
                        self.progress_bar["value"] = (current_file / total_files) * 100  # Update progress bar
                        self.output_window.update()  # Update the window to show the thumbnail
                    except Exception as e:
                        error_files += 1
                        list_errors.append(f"{src_path} > {dest_path} : FAILED with error {str(e)}")
                        self.output_box.insert(tk.END, f"{src_path} > {dest_path} : FAILED with error {str(e)}\n")
                        self.output_box.see(tk.END)  # Autoscroll


        self.finish_process(processed_files, total_files, duplicate_files, list_duplicates, error_files, list_errors)

    def finish_process(self, processed_files, total_files, duplicate_files, list_duplicates, error_files, list_errors):
        self.output_text.see(tk.END)  # Autoscroll
        if self.check_duplicates:
            self.output_text.insert(tk.END, "\n".join(list_duplicates) + "\n")
            self.output_text.see(tk.END)  # Autoscroll
        if list_errors:
            self.output_text.insert(tk.END, "\n".join(list_errors) + "\n")
            self.output_text.see(tk.END)  # Autoscroll
        self.output_text.insert(tk.END, f"Successfully imported {processed_files}/{total_files} files.\n")
        if self.check_duplicates:
            self.output_text.insert(tk.END, f"{duplicate_files} duplicates skipped.\n")
        if list_errors:
            self.output_text.insert(tk.END, f"{error_files} files failed to import.\n")
        self.output_box.insert(tk.END, "Processing complete!\n")
        self.output_box.see(tk.END)  # Autoscroll
        self.start_button.config(text="START", state="normal")
        if not list_errors:
            self.output_window.destroy()
        self.output_text.see(tk.END)  # Autoscroll
        
    def get_date_taken(self, path):
        try:
            with open(path, 'rb') as image_file:
                tags = exifread.process_file(image_file)
                # EXIF tags may contain 'EXIF DateTimeOriginal' or similar for the date
                date_taken_tag = tags.get('EXIF DateTimeOriginal', None) or tags.get('Image DateTime', None)
                if date_taken_tag:
                    return datetime.strptime(str(date_taken_tag), '%Y:%m:%d %H:%M:%S')
        except Exception as e:
            self.output_box.insert(tk.END, f"Error getting date taken for {path}: {e}\n")
            self.output_box.insert(tk.END, f"|__Defaulting to Modified Date\n")
        
        # Fallback to the file's modified date if no EXIF date is found
        return datetime.fromtimestamp(os.path.getmtime(path))


    def is_duplicate(self, src_path):
        src_hash = self.get_file_hash(src_path)
        return self.hash_map.get(src_hash)

    def get_file_hash(self, path):
        hasher = hashlib.md5()
        with open(path, 'rb') as afile:
            buf = afile.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def copy_file(self, src, dest):
        with open(src, 'rb') as fsrc:
            with open(dest, 'wb') as fdest:
                fdest.write(fsrc.read())

    def display_thumbnail(self, image_path):
        try:
            image = Image.open(image_path)
            image.thumbnail((200, 200))  # Create a thumbnail
            photo = ImageTk.PhotoImage(image)
            self.thumbnail_label.config(image=photo)
            self.thumbnail_label.image = photo  # Keep a reference to avoid garbage collection
        except Exception as e:
            self.output_box.insert(tk.END, f"Error displaying thumbnail for {image_path}: {e}\n")
        # Fake delay
        import time  # Import time module for sleep functionality
        time.sleep(2)
    
    
    def on_output_window_close(self):
        self.stop_processing = True

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageSorterGUI(root)
    root.mainloop()
