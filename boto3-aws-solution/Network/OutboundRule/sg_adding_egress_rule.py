import boto3

def create_egress_rules(group_id, rules):
  """
  Creates egress rules for a security group in AWS EC2.

  Args:
      group_id (str): The ID of the security group.
      rules (list): A list of dictionaries defining the egress rules. Each dictionary should have the following keys:
          protocol (str): The network protocol (e.g., "tcp", "udp").
          port_range (tuple): A tuple of integers representing the start and end ports (e.g., (80, 80) for a single port).
          cidr_block (str): The CIDR block specifying the allowed outbound traffic destination.
          description (str): An optional description for the rule.

  Returns:
      dict: The response from the AWS API call.
  """

  # Create an EC2 client object
  ec2 = boto3.client('ec2')

  for rule in rules:
    # Authorize egress traffic for the security group
    response = ec2.authorize_security_group_egress(
      GroupId=group_id,
      IpPermissions=[
        {
          'IpProtocol': rule['protocol'],
          'FromPort': rule['port_range'][0],
          'ToPort': rule['port_range'][1],
          'IpRanges': [
            {
              'CidrIp': rule['cidr_block'],
              'Description': rule['description']
            }
          ]
        }
      ]
    )

    # Print a success message with details
    print(f"Outbound rules are added successfully for {rule['cidr_block']} and port(s) {rule['port_range']}")

  return response

# Example usage (if running this script as the main program)
if __name__ == "__main__":
  group_id = 'sg-0eb0590edd65f2941'
  rules = [
    {
      'protocol': 'tcp',
      'port_range': (80, 80),
      'cidr_block': '192.168.1.112/32',
      'description': 'Allow HTTP Traffic'
    },
    {
      'protocol': 'tcp',
      'port_range': (443, 443),
      'cidr_block': '192.168.1.112/32',
      'description': 'Allow HTTPS Traffic'
    }
  ]

  create_egress_rules(group_id, rules)
