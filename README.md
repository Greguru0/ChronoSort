NOTE: This has been updated to a Python version. The Python version is much faster and has a GUI. It's far more sleek and I strongly recommend it for use.

# ChronoSort (Python)
Pretty much the same deal as below, except that it's far superior.

Ensure you have the following packages installed before running the script:  
Python 3.x  
Tkinter (usually comes with Python standard library)  
Pillow (PIL Fork)  

# ChronoSort (Powershell)
A PowerShell script for file organization. Arrange files from a source directory into a destination folder based on their creation date. Handle duplicates using MD5 hashing comparison. Destined filenames will follow ISO 8601 format with unique identifiers in the event of duplicate names.

&nbsp;&nbsp;&nbsp;&nbsp;


**Features:**  
Import and organize files (intended for photos and videos) from a source directory to a destination directory.  
Choose specific file types for the import process.  
Prevent overwriting of existing files with the same name using hash value comparison.  
Generate filenames following the ISO 8601 date format with unique identifiers to avoid conflicts.  

**Usage:**  
Run the script in a PowerShell environment.  
The script will prompt you to select the source folder containing the files to be imported.  
Next, choose the destination folder where the organized files will be placed.  
Specify the file types you want to include in the import process.  
Optionally choose to check for duplicate files (slower import) or skip duplicates (faster import).  
The script will then start the import process, organizing files by their creation dates.  

**Author:**  
-G
