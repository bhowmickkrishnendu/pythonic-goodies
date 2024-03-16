import os
import shutil


def copy_files(source_dir, dest_dir, filename):
  """
  Copies files from the source directory to the destination directory,
  matching filenames based on a provided filename pattern.

  Args:
      source_dir (str): The path to the directory containing the files to copy.
      dest_dir (str): The path to the destination directory where files will be copied.
      filename (str): The filename pattern (or part of the filename) to match for copying.
          This can be a complete filename or a substring to search within filenames.
  """

  # Ensure the destination directory exists, ignoring errors if it already exists.
  os.makedirs(dest_dir, exist_ok=True)

  # Walk through the source directory structure
  for root, dirs, files in os.walk(source_dir):
    for file in files:
      # Check if the filename matches the pattern
      if filename in file:
        # Construct the full paths for source and destination files
        source_path = os.path.join(root, file)
        dest_path = os.path.join(dest_dir, file)

        # Copy the file with preserved metadata (e.g., modification time)
        shutil.copy2(source_path, dest_path)
        print(f"File '{file}' copied successfully.")


def main():
  """
  Main function that reads filenames from a file and calls the copy_files function for each filename.
  """

  # Define directory paths
  source_dir = "D:\Family and Memories\Biyer Pic\D3500\Camera"
  dest_dir = "D:\Family and Memories\Biyer Pic\D3500\Working"
  filename_file = "file.txt"

  # Read filenames from the specified file
  with open(filename_file, "r") as f:
    filenames = f.read().splitlines()

  # Loop through each filename and copy matching files
  for filename in filenames:
    copy_files(source_dir, dest_dir, filename)


if __name__ == "__main__":
  main()
