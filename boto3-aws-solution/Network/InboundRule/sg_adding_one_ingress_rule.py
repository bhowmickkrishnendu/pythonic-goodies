import boto3
# Network:Security:InboundRule
# Developed by Krishnendu Bhowmick
# This function creates an inbound rule for a security group
# It takes the following parameters:
#   group_id: The ID of the security group to add the rule to
#   protocol: The protocol to allow (e.g., 'tcp', 'udp', 'icmp')
#   port_range: A tuple specifying the start and end ports to allow
#   cidr_block: The CIDR block to allow traffic from
#   description: A description for the rule
def create_inbound_rule(group_id, protocol, port_range, cidr_block, description):
    # Create a boto3 client for EC2
    ec2 = boto3.client('ec2')

    # Authorize the security group ingress rule
    response = ec2.authorize_security_group_ingress(
        GroupId=group_id,
        IpPermissions=[
            {
                'IpProtocol': protocol,
                'FromPort': port_range[0],
                'ToPort': port_range[1],
                'IpRanges': [
                    {
                        'CidrIp': cidr_block,
                        'Description': description
                    },
                ],
            },
        ],
    )

    print("Inbound rule added successfully")
    return response


# This is the main entry point of the script
if __name__ == "__main__":
    # Define the parameters for the inbound rule
    group_id = 'sg-0eb0590edd65f2941'
    protocol = 'tcp'
    port_range = (80, 80)
    cidr_block = '192.168.1.127/32'
    description = 'Allow local machine traffic'

    # Call the function to create the inbound rule
    create_inbound_rule(group_id, protocol, port_range, cidr_block, description)