# Network:Security:OutboundRules:Removal
# This module removes outbound rules from a security group
# It takes the following parameters:
#   group_id: Network:Security:GroupId - The ID of the security group to remove the outbound rules from
#   rules: Network:Security:OutboundRules:List - A list of outbound rules to be removed, where each rule is a dictionary containing:
#       protocol: Network:Protocol - The protocol of the outbound rule to remove (e.g., 'tcp', 'udp', 'icmp')
#       port_range: Network:Ports - A tuple specifying the start and end ports of the outbound rule to remove
#       cidr_block: Network:IPAddress:CIDR - The CIDR block of the outbound rule to remove

import boto3

# Network:Security:OutboundRules:Removal
def remove_outbound_rules(group_id, rules):
    # Network:Client
    ec2 = boto3.client('ec2')

    for rule in rules:
        # Network:Security:OutboundRule:Revocation
        response = ec2.revoke_security_group_egress(
            GroupId=group_id,
            IpPermissions=[
                {
                    'IpProtocol': rule['protocol'],
                    'FromPort': rule['port_range'][0],
                    'ToPort': rule['port_range'][1],
                    'IpRanges': [
                        {
                            'CidrIp': rule['cidr_block']
                        },
                    ],
                },
            ],
        )
        print(f"Outbound rule removed for {rule['cidr_block']}.")

    return response

# Network:Security:OutboundRules:Removal:Example
if __name__ == "__main__":
    group_id = 'sg-0eb0590edd65f2941'
    rules = [
        {
            'protocol': 'tcp',
            'port_range': (80, 80),
            'cidr_block': '192.168.1.112/32'
        },
        {
            'protocol': 'tcp',
            'port_range': (443, 443),
            'cidr_block': '192.168.1.112/32'
        }
    ]

    remove_outbound_rules(group_id, rules)