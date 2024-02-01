import subprocess

# Define the command to get the list of installed applications
command = 'wmic product get name'

# Execute the command
process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
output, error = process.communicate()

# Check for errors
if error:
    print("Error:", error.decode('utf-8'))
else:
    # Decode the output and split it into lines
    installed_apps = output.decode('utf-8').strip().split('\n')
    
    # Remove the first two lines which contain headers
    installed_apps = installed_apps[2:]

    # Save the list of installed applications to a text file
    with open('installed_apps.txt', 'w') as file:
        file.write('\n'.join(installed_apps))

    print("List of installed applications saved to installed_apps.txt")
