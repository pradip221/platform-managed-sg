'''Send notification to the end user for access AWS Console outside allowed Network'''
import os
import logging
import json
import boto3
import cfnresponse

ec2 = boto3.client('ec2')

# Logger
LOG_LEVEL = os.environ["LOG_LEVEL"]
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

def is_sg_exists_in_vpc(vpc_id, security_group_name):
    '''Check if the security group exists in the vpc'''
    logger.info('is_sg_exists_in_vpc:: vpc_id: %s, security_group_name: %s', 
        vpc_id, security_group_name)

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
    logger.info('describe_security_groups response: %s', response)
    return len(response['SecurityGroups']) > 0

def create_sg_in_vpc(vpc_id, security_group_name):
    '''Create a security group for the vpc'''
    logger.info('create_sg_in_vpc:: vpc_id: %s, security_group_name: %s', 
        vpc_id, security_group_name)
    response = ec2.create_security_group(
        GroupName=security_group_name,
        Description=f'Dynamically Hardened Platform Managed Security Group for {vpc_id}',
        VpcId=vpc_id
    )
    logger.info('create_security_group response: %s', response)
    return response['GroupId']

def create_sg_if_not_exists(security_group_name):
    '''Get all VPCs, check if platform managed SG exists in the VPC and if not, create it'''
    vpcs = ec2.describe_vpcs()
    logger.info('describe_vpcs: %s', vpcs)

    for vpc in vpcs['Vpcs']:
        vpc_id = vpc['VpcId']

        if is_sg_exists_in_vpc(vpc_id, security_group_name):
            #  skip creating security group for the vpc
            logger.info("Security Group %s already exists in VPC %s, so skipping creating the same...", security_group_name, vpc_id)
            
        else:
            # Create security group for vpc
            security_group_id = create_sg_in_vpc(vpc_id, security_group_name)
            logger.info("Security Group %s Created in VPC %s", security_group_id, vpc_id)
                
def lambda_handler(event, context):
    '''lambda_handler'''
    try:
        response_data = {}
        logger.info("event: %s", json.dumps(event))
        request_type = event['RequestType']
        security_group_name = event['ResourceProperties']['SecurityGroupName']

        if request_type == 'Create' or request_type == 'Update':
            create_sg_if_not_exists(security_group_name)
            
        elif request_type == 'Delete':
            logger.info('Skipping Delete...')
        
        else:
            raise ValueError("request_type must be Create/Update/Delete") 

        # Send SUCCESS response to CFN
        cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)

    except Exception as exception:
        logger.error('ERROR: %s', exception)
        # Send FAILED response to CFN
        cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
            