'''Send notification to the end user for access AWS Console outside allowed Network'''
import os
import logging
import json
import csv
import boto3
import dns.resolver

ec2 = boto3.client('ec2')

# Logger
LOG_LEVEL = os.environ["LOG_LEVEL"]
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

def resolve_domain_ips(domains):
    '''Resolves the IPs of the AD domains'''
    domain_ips_dict = {}
    for domain in domains:
        results = dns.resolver.query(domain, 'A')
        domain_ips = []
        for ipval in results:
            domain_ips.append(ipval.to_text())
        domain_ips_dict[domain] = domain_ips
    logger.info('domain_ips_dict: %s', domain_ips_dict)
    # domain_ips_dict = {
    #     "example.com": [
    #         "1.1.1.1",
    #         "2.2.2.2"
    #     ],
    #     "google.com": [
    #         "4.4.4.4"
    #     ]
    # }
    return domain_ips_dict

def build_sg_rules_for_domain_ips_from_csv(domain_ips_dict):
    '''Read csv to get the standard rules for security groups
       and build the final expected sg rules combining with the AD resolved IPs
    '''
    with open('sg_rules.csv', 'r', encoding='utf-8-sig') as csvfile:
        csv_rules = csv.DictReader(csvfile)
        expected_rules = {}
        for csv_rule in csv_rules:
            for domain, domain_ips in domain_ips_dict.items():
                for domain_ip in domain_ips:
                    row = dict(csv_rule).copy()
                    row['domain'] = domain
                    row['domain_ip'] = domain_ip
                    expected_rules[f"{csv_rule['protocol']}-{csv_rule['from_port']}-{csv_rule['to_port']}-{domain_ip}/32"] = row

    logger.debug('csv rows: %s', json.dumps(expected_rules))
    return expected_rules

def get_current_sg_rules(vpc_id, security_group_name):
    '''Fetch the sg details per vpc and prepare the current rules dict
       with key as 'IpProtocol-FromPort-ToPort-CidrIp'
    '''
    response = ec2.describe_security_groups(
        Filters=[
            {
                'Name': 'group-name',
                'Values': [
                    security_group_name,
                ]
            },
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id,
                ]
            },
        ]
    )
    logger.debug('describe_security_groups response: %s', json.dumps(response))

    security_group_id = response['SecurityGroups'][0]['GroupId']
    ingress_rules = response['SecurityGroups'][0]['IpPermissions']
    current_rules = []
    for ingress_rule in ingress_rules:
        for ip_range in ingress_rule['IpRanges']:
            key = f"{ingress_rule['IpProtocol']}-{ingress_rule['FromPort']}-{ingress_rule['ToPort']}-{ip_range['CidrIp']}"
            current_rules.append(key)

    logger.info('current_rules for security_group %s in %s:: %s',
                    security_group_name, vpc_id, current_rules)
    return security_group_id, current_rules

def create_sg_rule(security_group_id, expected_rule):
    '''Create Security Group rule with Name Tags & Description out of the expected rule'''
    ip_protocol = expected_rule['protocol']
    cidr_ip = f"{expected_rule['domain_ip']}/32"
    from_port = int(expected_rule['from_port'])
    to_port = int(expected_rule['to_port'])

    # Create SG rule
    response = ec2.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpProtocol=ip_protocol,
        CidrIp=cidr_ip,
        FromPort=from_port,
        ToPort=to_port,
        TagSpecifications=[
            {
                'ResourceType': 'security-group-rule',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': f"{expected_rule['domain']}-{ip_protocol}-{from_port}-{to_port}"
                    },
                ]
            },
        ]
    )
    logger.debug('authorize_security_group_ingress response: %s', response)

    # Update description of the sg rule
    ec2.update_security_group_rule_descriptions_ingress(
        GroupId=security_group_id,
        SecurityGroupRuleDescriptions=[
            {
                'SecurityGroupRuleId': response['SecurityGroupRules'][0]['SecurityGroupRuleId'],
                'Description': expected_rule['description']
            },
        ]
    )

def lambda_handler(event, _context):
    '''lambda_handler'''
    try:
        logger.info("event: %s", json.dumps(event))
        security_group_name = os.environ["SECURITY_GROUP_NAME"]

        domain_ips_dict = resolve_domain_ips(event["domains"])
        expected_rules = build_sg_rules_for_domain_ips_from_csv(domain_ips_dict)

        vpcs = ec2.describe_vpcs()
        for vpc in vpcs['Vpcs']:
            vpc_id = vpc['VpcId']
            security_group_id, current_rules = get_current_sg_rules(vpc_id, security_group_name)
            
            for key, expected_rule in expected_rules.items():
                if key not in current_rules:
                    logger.info('New sg rule to be inserted for sg: %s in %s is "%s"', 
                        security_group_name, vpc_id, key)
                    create_sg_rule(security_group_id, expected_rule)
                    
                else:
                    logger.info('SG rule "%s" already exists for sg: %s in %s, skipping...', 
                        key, security_group_name, vpc_id)
                        
        logger.info('Lambda executed succeesfully')
    
    except Exception as exception:
        logger.error('ERROR: %s', exception)
        raise exception
