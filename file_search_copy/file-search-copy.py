import os
import shutil

def copy_files(source_dir, dest_dir, filename):
    # Ensure the destination directory exists
    os.makedirs(dest_dir, exist_ok=True)
    
    # Iterate over files in the source directory
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            # Check if the file name matches the pattern from file.txt
            if filename in file:
                # Construct the source and destination paths
                source_path = os.path.join(root, file)
                dest_path = os.path.join(dest_dir, file)
                
                # Copy the file to the destination directory
                shutil.copy2(source_path, dest_path)
                print(f"File '{file}' copied successfully.")

def main():
    # Source directory containing the files
    source_dir = "D:\Family and Memories\Biyer Pic\D3500\Camera"
    
    # Destination directory where files will be copied
    dest_dir = "D:\Family and Memories\Biyer Pic\D3500\Working"
    
    # File containing the filenames to be copied (file.txt)
    filename_file = "file.txt"
    
    # Read filenames from file.txt
    with open(filename_file, "r") as f:
        filenames = f.read().splitlines()
    
    # Iterate over each filename and copy the corresponding files
    for filename in filenames:
        copy_files(source_dir, dest_dir, filename)

if __name__ == "__main__":
    main()
