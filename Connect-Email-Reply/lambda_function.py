import json
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
import os


casesclient = boto3.client('connectcases')
cpclient = boto3.client('customer-profiles')
ses = boto3.client("ses")
s3 = boto3.client("s3")

#CONNECT_INSTANCE_ID = os.environ['CONNECT_INSTANCE_ID']
CUSTOMER_PROFILE_DOMAIN = os.environ['CUSTOMER_PROFILE_DOMAIN']
CASES_DOMAIN = os.environ['CASES_DOMAIN']
SOURCE_EMAIL = os.environ['SOURCE_EMAIL']


def lambda_handler(event, context):
    print(event)
    
    
    if (event['detail']['relatedItem']['relatedItemType'] == 'comment'):
        if('user' in event['detail']['performedBy']):
            user = event['detail']['performedBy']['user']['userArn']
            
        msgBody = event['detail']['relatedItem']['comment']['body']
        caseId = event['detail']['relatedItem']['caseId']
        caseDetails = get_case_details(caseId)
        
        customerProfile = search_customer_profile('_profileId',caseDetails['customer_id'])
        
        send_email([customerProfile['EmailAddress']],caseDetails['title'], msgBody, False)
        
    else:
        print("No comment added")
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def get_case_details(caseId):
    
    try:
        caseResponse = casesclient.get_case(
        caseId=caseId,
        domainId=CASES_DOMAIN,
        fields=[
            {
                'id': 'customer_id'
                
            },
            {
                'id':'title'
                
            }
        ]
        )
        
    except ClientError as e:
        print(f'Error getting case: {e}')
        return False
    else:
        return extract_values(caseResponse['fields'])

def search_customer_profile(keyname,keyvalue):
    try:
        cp = cpclient.search_profiles(DomainName=CUSTOMER_PROFILE_DOMAIN,KeyName=keyname,Values=[keyvalue])
    except ClientError as e:
        print(f'Error searching profile: {e}')
    else:
        if(len(cp['Items'])):
            return cp['Items'][0]
        else:
            return False


def send_email(destination,subject, content, files):

    CHARSET = "utf-8"
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = SOURCE_EMAIL 
    msg['To'] = destination[0]
    
    msg_body = MIMEMultipart('alternative')

    textpart = MIMEText(content.encode(CHARSET), 'plain', CHARSET)
    msg_body.attach(textpart)
    msg.attach(msg_body)
    BODY_HTML= '<html><head></head><body><p>'+content+'<img src="cid:firma">'+'</p></body></html>'
    htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
    msg_body.attach(htmlpart)


    if (files and len(files)>0):
        print(files)
        for file in files:
            print("Getting file")
            print(CONNECT_ATTACHMENTS_LOCATION + '/' + file['fileLocation'])
            s3.download_file(BUCKET, CONNECT_ATTACHMENTS_LOCATION + '/' + file['fileLocation'], '/tmp/' +file['attachmentName'])
            att = MIMEApplication(open('/tmp/' +file['attachmentName'], 'rb').read())
            att.add_header('Content-Disposition','attachment',filename=os.path.basename('/tmp/' +file['attachmentName']))
            msg.attach(att)

    try:
        response = ses.send_raw_email(
            Source=SOURCE_EMAIL,
            Destinations=
                destination
            ,
            RawMessage={
                'Data':msg.as_string(),
            },
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

def extract_values(data):
    result = {}
    for item in data:
        if item['id'] == 'title':
            result['title'] = item['value']['stringValue']
        elif item['id'] == 'customer_id':
            customer_id = item['value']['stringValue'].split('/')[-1]
            result['customer_id'] = customer_id
    return result