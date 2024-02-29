import boto3

def remove_outbound_rules(group_id, rules):
    ec2 = boto3.client('ec2')

    for rule in rules:
        response = ec2.revoke_security_group_egress(
            GroupId = group_id,
            IpPermissions = [
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
        print(f"Outbount rule removed for {rule['cidr_block']}.")
    
    return response
# end def

# Network:Security:OutboundRules:Removal

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
