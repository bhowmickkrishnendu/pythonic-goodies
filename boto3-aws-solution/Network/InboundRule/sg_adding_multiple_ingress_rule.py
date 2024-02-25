# Network:Security:InboundRules
# This module, developed by Krishnendu Bhowmick, creates multiple inbound rules for a security group
# It takes the following parameters:
#   group_id: Network:Security:GroupId - The ID of the security group to add the rules to
#   rules: Network:Security:InboundRules:List - A list of rules to be added, where each rule is a dictionary containing:
#       protocol: Network:Protocol - The protocol to allow (e.g., 'tcp', 'udp', 'icmp')
#       port_range: Network:Ports - A tuple specifying the start and end ports to allow
#       cidr_block: Network:IPAddress:CIDR - The CIDR block to allow traffic from
#       description: Network:Security:InboundRule:Description - A description for the rule

import boto3

# Network:Security:InboundRules:Creation
def create_inbound_rules(group_id, rules):
    # Network:Client
    ec2 = boto3.client('ec2')

    for rule in rules:
        # Network:Security:InboundRule:Authorization
        response = ec2.authorize_security_group_ingress(
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
                        },
                    ],
                },
            ],
        )
        print(f"Inbound rule added successfully for {rule['cidr_block']}.")

    return response

# Network:Security:InboundRules
if __name__ == "__main__":
    group_id = 'sg-0eb0590edd65f2941'
    rules = [
        {
            'protocol': 'tcp',
            'port_range': (80, 80),
            'cidr_block': '192.168.0.100/32',
            'description': 'Allow HTTP traffic'
        },
        {
            'protocol': 'tcp',
            'port_range': (443, 443),
            'cidr_block': '192.168.1.100/32',
            'description': 'Allow HTTPS traffic'
        }
    ]

    create_inbound_rules(group_id, rules)