# Network:Security:InboundRules:Removal
# This module, developed by Krishnendu Bhowmick, removes multiple inbound rules from a security group
# It takes the following parameters:
#   group_id: Network:Security:GroupId - The ID of the security group to remove the rules from
#   rules: Network:Security:InboundRules:List - A list of rules to be removed, where each rule is a dictionary containing:
#       protocol: Network:Protocol - The protocol of the rule to remove (e.g., 'tcp', 'udp', 'icmp')
#       port_range: Network:Ports - A tuple specifying the start and end ports of the rule to remove
#       cidr_block: Network:IPAddress:CIDR - The CIDR block of the rule to remove

import boto3

# Network:Security:InboundRules:Removal
def remove_inbound_rules(group_id, rules):
    # Network:Client
    ec2 = boto3.client('ec2')

    for rule in rules:
        # Network:Security:InboundRule:Revocation
        response = ec2.revoke_security_group_ingress(
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
        print(f"Inbound rule removed successfully for {rule['cidr_block']} and {rule['port_range']}.")

    return response

# Network:Security:InboundRules:Removal
if __name__ == "__main__":
    group_id = 'sg-0eb0590edd65f2941'
    rules_to_remove = [
        {
            'protocol': 'tcp',
            'port_range': (80, 80),
            'cidr_block': '192.168.1.127/32',
        },
        {
            'protocol': 'tcp',
            'port_range': (80, 80),
            'cidr_block': '0.0.0.0/0',
        },
        {
            'protocol': 'tcp',
            'port_range': (80, 80),
            'cidr_block': '192.168.0.100/32',
        },
        {
            'protocol': 'tcp',
            'port_range': (443, 443),
            'cidr_block': '192.168.1.100/32',
        }
    ]

    remove_inbound_rules(group_id, rules_to_remove)