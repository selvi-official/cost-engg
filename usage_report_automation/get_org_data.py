import boto3
from mysql.connector import connection
import mysql.connector
import calendar
from datetime import *
from dateutil.relativedelta import *
from math import *
import requests
import json
import boto3
from google.cloud.billing import budgets
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os


def getFewFieldsFromExcel():
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/ec2-user/mailer/budgets/GCP/serviceaccountcred.json'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SAMPLE_SPREADSHEET_ID = '1QWDhM4F7hNG0Uapyb23FOzpipHAcd7PXF0ISGLei-Wc'
    SAMPLE_RANGE_NAME = 'Budgets For Cost Engg Team!A2:Z'

    creds = None
    budget = {}
    acc = {}
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('/home/ec2-user/mailer/budgets/GCP/token.json'):
        creds = Credentials.from_authorized_user_file('/home/ec2-user/mailer/budgets/GCP/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '/home/ec2-user/mailer/budgets/GCP/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('/home/ec2-user/mailer/budgets/GCP/token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)
        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        values = result.get('values', [])

        if not values:
            print('No data found.')
            return
        else:
            for i in values:
                acc[i[0]] = {'product':i[15], 'bu':str(i[18].split(" "))[0], 'cogs_ind':i[16]}

        return acc
    except:
        pass

conn = connection.MySQLConnection(
    user='admin',
    host='cost-eng.cnnuygjl0vgg.us-east-1.rds.amazonaws.com',
    database='cost',
    password='***'
)

data_list ={'freshworks-payer': '031429593201'}
mycursor = conn.cursor()

acc = getFewFieldsFromExcel()
try:

    client = boto3.client('sts')
    response = client.assume_role(RoleArn="arn:aws:iam::031429593201:role/fusion_app",
                                      RoleSessionName="get_org_info")
    org_client = boto3.client('organizations', aws_access_key_id=response['Credentials']['AccessKeyId'],
                                   aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                                   aws_session_token=response['Credentials']['SessionToken'])
    paginator = org_client.get_paginator('list_accounts')
    accounts = []
    poc_details = []
    
    for page in paginator.paginate():
        accounts.extend(page['Accounts'])
    
    for account in accounts:
        response1 = org_client.list_tags_for_resource(ResourceId=account['Id'])
        tags = {tag['Key']: tag['Value'] for tag in response1['Tags']}
        poc = [tags.get('own:primary'), tags.get('own:secondary')]
        if tags.get('devops:poc') is not None:
            poc = [tags.get('devops:poc')]+poc
        poc.remove(account['Email'])
        poc_details.append([account['Id'],account['Name'],tags.get('security:environment').split(":")[1]],account['Status'],poc[0],account['Email'],poc[0],poc[0])
except:
    pass

mycursor.execute(f"select account_id from aws_accounts_ur;")
existingIds = [i[0] for i in mycursor.fetchall()]

records_to_insert = []

for record in poc_details:
    if record[0] not in existingIds:
        records_to_insert.append(record)


if records_to_insert :
    insertToMasterTable = "insert into aws_accounts_ur(`account_id`,`account_name`,`environment`,`product`,`bu`,`cogs_ind`,`active`,`account_owner`,`team_dl`,`manager_email`,`director_email`) values(%s,%s,%s,%s,%s,%s,%s,%s);"
    mycursor.executemany(insertToMasterTable, records_to_insert)


else:
    updateBudgetTable = '''UPDATE aws_accounts_ur
                            SET
                                account_name = %s,
                                environment = %s,
                                product =  %s,
                                bu = %s,
                                cogs_ind = %s,
                                active = %s,
                                account_owner = %s,
                                team_dl = %s,
                                manager_email = %s,
                                director_email = %s
                            WHERE account_id = %s and account_owner != %s;
                        '''


    mycursor.executemany(updateBudgetTable, poc_details+poc_details[-1:])

conn.commit()







