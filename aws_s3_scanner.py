import subprocess
import json

# Get list of S3 buckets
bucket_list = subprocess.check_output(['aws', 's3', 'ls'], universal_newlines=True).splitlines()

# Iterate through each bucket
for bucket_info in bucket_list:
    bucket_name = bucket_info.split()[-1]
    print(f"Checking bucket: {bucket_name}")
    
    # List files in the bucket
    try:
        files = subprocess.check_output(['aws', 's3', 'ls', f's3://{bucket_name}', '--recursive'], universal_newlines=True)
        env_files = [line.split()[-1] for line in files.splitlines() if '.env' in line]
        
        for env_file in env_files:
            print(f"Found .env file: {env_file}")
            
            # Check if the file is publicly accessible
            acl_output = subprocess.check_output(['aws', 's3api', 'get-object-acl', '--bucket', bucket_name, '--key', env_file], universal_newlines=True)
            acl = json.loads(acl_output)
            
            for grant in acl['Grants']:
                if 'URI' in grant['Grantee'] and 'AllUsers' in grant['Grantee']['URI']:
                    print(f".env file is publicly accessible: {env_file}")
                else:
                    print(f".env file is not publicly accessible: {env_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error checking bucket {bucket_name}: {e}")
