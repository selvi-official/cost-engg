import boto3
data_list ={'freshworks-payer': '031429593201'}

try:
    client = boto3.client('sts')
    response = client.assume_role(RoleArn="arn:aws:iam::031429593201:role/fusion_app",
                                      RoleSessionName="get_org_info")
    org_client = boto3.client('organizations', aws_access_key_id=response['Credentials']['AccessKeyId'],
                                   aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                                   aws_session_token=response['Credentials']['SessionToken'])
    paginator = org_client.get_paginator('list_accounts')
    accounts = []
    
    for page in paginator.paginate():
        accounts.extend(page['Accounts'])
    
    for account in accounts:
        response1 = org_client.list_tags_for_resource(ResourceId=account['Id'])
        tags = {tag['Key']: tag['Value'] for tag in response1['Tags']}
        poc = [tags.get('own:primary'), tags.get('own:secondary')]
        if tags.get('devops:poc') is not None:
            poc = [tags.get('devops:poc')]+poc
        poc_details = [account['Id'],account['Name'],account['Status'],poc[0],account['Email'],tags.get('security:environment').split(":")[1]]
        print(*poc_details,sep="|")

except Exception as e:
    print(e)



