import boto3

def create_egress_rules(group_id, rules):
    # Network:client
    ec2 = boto3.client('ec2')

    for rule in rules:
        # Network:Security:InboundRule:Authorization
        response = ec2.authorize_security_group_egress(
            GroupId=group_id,
            IpPermissions=[
                {
                    'IpProtocol': rule['protocol'],
                    'FromPort': rule['port_range'][0],
                    'ToPort': rule['prot_range'][1],
                    'IpRanges': [
                        {
                            'CidrIp': rule['cidr_block'],
                            'Description': rule['description']
                        },
                    ],
                },
            ],
        )
        print(f"Outbound rules are added successfully for {rule['cidr_block']} and {rule['port_range']}")

    return response

