from mysql.connector import connection
import mysql.connector
import calendar
from datetime import *
from dateutil.relativedelta import *
from math import *
import requests
import json
import boto3
from datetime import date
from google.cloud.billing import budgets
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os

conn = connection.MySQLConnection(
    user='admin',
    host='cost-eng.cnnuygjl0vgg.us-east-1.rds.amazonaws.com',
    database='cost',
    password='costdb3306'
)
mycursor = conn.cursor()

sts = boto3.client('sts')
assumed_role_object = sts.assume_role(
    RoleArn="arn:aws:iam::031429593201:role/fusion_app",
    RoleSessionName="freshworks-payer"
)
credentials = assumed_role_object['Credentials']

# Initialize Cost Explorer client
client = boto3.client(
    'ce',
    aws_access_key_id=credentials['AccessKeyId'],
    aws_secret_access_key=credentials['SecretAccessKey'],
    aws_session_token=credentials['SessionToken'],
    region_name='us-east-1'
)


def getBudget(getAccs):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/ec2-user/mailer/budgets/GCP/serviceaccountcred.json'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SAMPLE_SPREADSHEET_ID = '1QWDhM4F7hNG0Uapyb23FOzpipHAcd7PXF0ISGLei-Wc'
    SAMPLE_RANGE_NAME = 'Budgets For Cost Engg Team!A2:Z'

    creds = None
    budget = {}
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
                mycursor.execute(f"select account_id from aws_accounts_ur where account_name = '{i[0]}' limit 1;")
                res = mycursor.fetchall()
                if len(i[13])!=12:
                    acc_id = res[0][0]
                else:
                    acc_id = i[13]
                if acc_id not in getAccs :
                    if i[14] == 'Production': 
                        lock_flag = False
                        #print("if if"+" "+lock_flag)
                    else:
                        lock_flag = True
                        #print("if else"+" "+lock_flag)
                elif getAccs[acc_id] == 'production':
                    lock_flag = False
                    #print("elif"+" "+lock_flag)
                else:
                    lock_flag = True
                    #print("else"+" "+lock_flag)
                actual_budget = i[7][1:]
                if ',' in i[7]:
                    actual_budget = i[7][1:].replace(",","")
                budget[acc_id] = [actual_budget, lock_flag]
                print(acc_id, budget[acc_id])
    except HttpError as err:
        print(err)

    budgetDct = {}
    unbudgetAccs = []
 
    for i in getAccs:
        if i not in budget:
            unbudgetAccs.append(i)
            budgetDct[i] = 0
        else:
            budgetDct[i] = budget[i]

    print("unbudgetAccs")
    print(unbudgetAccs)
    print("-"*50)
    print(budgetDct)
    return budgetDct

def getUsage():
    history = client.get_cost_and_usage(
    TimePeriod={
        'Start': datetime.today().replace(day=1).strftime('%Y-%m-%d'),
        'End': (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    },
    Filter={
        'Not': {
            'Dimensions': {
                'Key': 'RECORD_TYPE',
                'Values': [
                    'REFUND', 'Support', 'Tax', 'Credit'
                ]
            }
        }
    },
    Granularity='MONTHLY',
    Metrics=['NetAmortizedCost'],
    GroupBy=[
        {
            'Type': 'DIMENSION',
            'Key': 'LINKED_ACCOUNT'
        },
    ]
    )
    return history['ResultsByTime']

mycursor.execute(f"select account_id,environment from aws_accounts_ur;")
getAccs = {}
for i in mycursor.fetchall():
    getAccs[i[0]] = i[1]

                                 
accBudgets = getBudget(getAccs)
accUsage = getUsage()


# Dictionary to store account usage forecast
acc_budget_usage_forecast = {}
error = []
today = datetime.today()

# Process historical data and get forecast
for i in accUsage:
    dt = today.replace(day=1)
    for j in i['Groups']:
        if j['Keys'][0] in accBudgets:
            budg = accBudgets[j['Keys'][0]]
        else:
            if j['Keys'][0] not in getAccs:
                error.append(j['Keys'][0]+"|"+"Not in master")
            else:
                if getAccs[j['Keys'][0]] == 'production':
                    budg = [0, False]
                else:
                    budg = [0 , True]
            error.append(j['Keys'][0]+"|"+"NO BUDGET")
        try:
            history2 = client.get_cost_forecast(
                TimePeriod={
                    'Start': datetime.today().strftime('%Y-%m-%d'),
                    'End': (datetime.today() + timedelta(days=30)).replace(day=1).strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metric='NET_AMORTIZED_COST',
                Filter={
                    'And': [
                        {
                            'Dimensions': {
                                'Key': 'LINKED_ACCOUNT',
                                'Values': [j['Keys'][0]]
                            }
                        },
                        {
                            'Not': {
                                'Dimensions': {
                                    'Key': 'RECORD_TYPE',
                                    'Values': [
                                        'REFUND', 'Support', 'Tax', 'Credit'
                                    ]
                                }
                            }
                        }
                    ]
                }
                )
            fc = history2['ForecastResultsByTime'][0]['MeanValue']
        except Exception as e:
            fc = 0
            error.append(j['Keys'][0]+"|"+"NO FORECAST")

        if j['Keys'][0] == '637423193711':
            print(budg, accBudgets[j['Keys'][0]])
        acc_budget_usage_forecast[j['Keys'][0]] = {
            "Budget": budg,
            "Usage": j['Metrics']['NetAmortizedCost']['Amount'],
            "Forecast": fc
        }

print(error)
print("-"*50)

for i in getAccs.keys():
    if i not in acc_budget_usage_forecast:
        if i not in accBudgets:
            if getAccs[i] == 'production':
                budg = [0, False]
                print("if")
            else:
                budg = [0, True]
                print("ifelse")
        else:
            budg = accBudgets[i]
            print("else");print(budg)
        acc_budget_usage_forecast[i] = {'Budget': budg, 'Usage':0, 'Forecast':0}
        quit()
    elif "Usage" not in acc_budget_usage_forecast[i]:
        acc_budget_usage_forecast[i]["Usage"] = 0
        print("No usage"+i)
    elif "Forecast" not in acc_budget_usage_forecast[i]:
        acc_budget_usage_forecast[i]["Forecast"] = 0
        print("No forecast"+i)



listToInsert = []
updaterecords = [] 
quarter = 'Q'+str((today.month - 1) // 3 + 1 )
for i in acc_budget_usage_forecast:
    listToInsert.append([i,today.year, today.month, quarter,float(acc_budget_usage_forecast[i]['Budget'][0]), float(acc_budget_usage_forecast[i]['Usage']),float(acc_budget_usage_forecast[i]['Forecast']), acc_budget_usage_forecast[i]['Budget'][1] ])
    updaterecords.append([float(acc_budget_usage_forecast[i]['Usage']), float(acc_budget_usage_forecast[i]['Forecast']), float(acc_budget_usage_forecast[i]['Budget'][0]), acc_budget_usage_forecast[i]['Budget'][1], float(acc_budget_usage_forecast[i]['Budget'][0]), float(acc_budget_usage_forecast[i]['Budget'][0]), today.month,today.year,quarter,i ])


#check count of records if it has already for current month
mycursor.execute(f"select count(*) from aws_account_budgets_ur where month={today.month} and year={today.year} and quarter='{quarter}';")
checkCurrentMonthEntry = mycursor.fetchall()



if checkCurrentMonthEntry[0][0] == 0 :
    insertToBudgetTable = "insert into aws_account_budgets_ur(`account_id`,`year`,`month`,`quarter`,`acc_budget`,`acc_usage`,`acc_forecast`,`lock_flag`) values(%s,%s,%s,%s,%s,%s,%s,%s);"
    mycursor.executemany(insertToBudgetTable, listToInsert)


else:
    updateBudgetTable = '''UPDATE aws_account_budgets_ur
                            SET
                                acc_usage = %s,
                                acc_forecast = %s,
                                lock_flag = CASE
                                              WHEN acc_budget != %s THEN %s
                                              ELSE lock_flag
                                            END,
                                acc_budget = CASE
                                                WHEN acc_budget != %s THEN %s
                                                ELSE acc_budget
                                              END
                            WHERE month = %s
                              AND year = %s
                              AND quarter = %s
                              AND account_id = %s;
                        '''


    mycursor.executemany(updateBudgetTable, updaterecords)

conn.commit()







