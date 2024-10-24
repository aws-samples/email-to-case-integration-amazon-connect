import json
import boto3
from botocore.exceptions import ClientError
import os
import requests
import sys
from email import policy
from email.parser import BytesParser
from urllib.parse import unquote


cpclient = boto3.client('customer-profiles')
casesclient = boto3.client('connectcases')
s3 = boto3.client('s3')
connectclient= boto3.client('connect')

CONNECT_INSTANCE_ID = os.environ['CONNECT_INSTANCE_ID'] 
CUSTOMER_PROFILE_DOMAIN = os.environ['CUSTOMER_PROFILE_DOMAIN']
CASES_DOMAIN = os.environ['CASES_DOMAIN']
CASE_TEMPLATE= os.environ['CASE_TEMPLATE']


AWS_REGION = os.environ['AWS_REGION']

def lambda_handler(event, context):
    print(event)
    aws_account_id = context.invoked_function_arn.split(":")[4]
    

    for rec in event['Records']:
        fileKey = unquote(unquote(rec['s3']['object']['key']))
        bucket = rec['s3']['bucket']['name']

        obj = s3.get_object(Bucket=bucket, Key=fileKey)
        raw_mail = obj['Body'].read()
        
        msg = BytesParser(policy=policy.default).parsebytes(raw_mail)
        msgFrom = strip_address((msg.get('From')))
        msgSubject=msg.get('Subject')

        
        msgBody=""
        files = []
        if msg.is_multipart():
            for part in msg.walk():
                
                ctype = part.get_content_type()
                content_type = str(part.get('Content-Type'))
                content_disposition = str(part.get('Content-Disposition'))

                
                
                fileAttached = {}
                if content_disposition and 'attachment' in content_disposition:
                    fileAttached['name'] = part.get_filename()
                    fileAttached['type'] = part.get_content_type()
                    fileAttached['data'] = part.get_content()
                    fileAttached['size'] = sys.getsizeof(fileAttached['data']) - 33 ## Removing BYTES overhead
                    
                    files.append(fileAttached)
                    
                
                elif ctype == 'text/plain':
                    try:
                        body = part.get_payload(decode=True)
                        msgBody += body.decode()
                        
                    except Exception as err:
                        print(err)
                        print("Attempting decoding as latin1")
                        body = part.get_payload(decode=True).decode('latin1')
                        msgBody += body
                    
                    
        # not multipart 
        else:
            print("Not multipart")
            try:
                body = part.get_payload(decode=True)
                msgBody += body.decode()
                
            except Exception as err:
                print(err)
                print("Attempting decoding as latin1")
                body = part.get_payload(decode=True).decode('latin1')
                msgBody += body
            
        response = search_customer_profile('_email',msgFrom)
        
        if response is not None:
            print("Creating case")
            profileid = response['ProfileId']
            userArn = f"arn:aws:profile:{AWS_REGION}:{aws_account_id}:domains/{CUSTOMER_PROFILE_DOMAIN}/profiles/{profileid}"
            caseArn = create_case(msgSubject,userArn)
            response = post_comment(caseArn, msgBody)
            
            
        else:
            print("Create profile")
            profileid = create_profile(msgFrom)
            
            userArn = f"arn:aws:profile:{AWS_REGION}:{aws_account_id}:domains/{CUSTOMER_PROFILE_DOMAIN}/profiles/{profileid}"
            caseArn = create_case(msgSubject,userArn)
            response = post_comment(caseArn, msgBody)
            
            
        
        
        if(len(files)>0):
            for file in files:
                attachmentResponse = attach_file(file['data'],file['name'],file['size'],file['type'],caseArn)
                
                if(not attachmentResponse):
                    print("Attachment was not successfull")
                    s3File = upload_data_to_s3(file['data'],bucket,  'attachments/'+ fileKey+file['name'])
                    
                    

    return {
        'statusCode': 200,
        'body': json.dumps('Sent!')
    }


def search_customer_profile(keyname,keyvalue):
    try:
        cp = cpclient.search_profiles(DomainName=CUSTOMER_PROFILE_DOMAIN,KeyName=keyname,Values=[keyvalue])
    except ClientError as e:
        print(f'Error searching profile: {e}')
    else:
        if(len(cp['Items'])):
            return cp['Items'][0]
        else:
            return None


def create_profile(email):
    response = cpclient.create_profile(DomainName=CUSTOMER_PROFILE_DOMAIN,EmailAddress=email)
    return response['ProfileId']


def create_case(subject,userArn):
    
    try:
        caseResponse = casesclient.create_case(
            #clientToken='string',
            domainId=CASES_DOMAIN,
            fields=[
                {
                    'id': 'customer_id',
                    'value': {
                        'stringValue': userArn
                    }
                },
                {
                    'id': 'title',
                    'value': {
                        'stringValue': subject
                    }
                }
            ],

            templateId=CASE_TEMPLATE
            
            )
    except ClientError as e:
        print(f'Error creaating case: {e}')
    else:
        if('caseArn' in caseResponse):
            return caseResponse['caseArn']
        else:
            return None


def strip_address(address):
    # Extract address
    idx1 = address.find('<')
    idx2 = address.find('>')

    if idx1 > 0 and idx2 > 0:
        return address[idx1 + 1: idx2]
    else:
        return address

def upload_data_to_s3(bytes_data,bucket_name, s3_key):
    s3_resource = boto3.resource('s3')
    obj = s3_resource.Object(bucket_name, s3_key)
    obj.put(ACL='private', Body=bytes_data)

    s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
    return s3_url


def attach_file(fileData,fileName,fileSize,fileType,caseArn):
    
    try:
        attachResponse = connectclient.start_attached_file_upload(
            #ClientToken='string',
            InstanceId=CONNECT_INSTANCE_ID,
            FileName=fileName,
            FileSizeInBytes=fileSize,
            FileUseCaseType='ATTACHMENT',
            AssociatedResourceArn=caseArn
            )
        print("attachResponse",attachResponse)
    except ClientError as e:
        print("Error while creating attachment")
        if(e.response['Error']['Code'] =='AccessDeniedException'):
            print(e.response['Error'])
            raise e
        elif(e.response['Error']['Code'] =='ValidationException'):
            print(e.response['Error'])
            return None
    else:
        try:
            filePostingResponse = requests.put(attachResponse['UploadUrlMetadata']['Url'], 
            data=fileData,
            headers=attachResponse['UploadUrlMetadata']['HeadersToInclude'])
        except ClientError as e:
            print("Error while uploading")
            print(e.response['Error'])
            raise e
        else:
            print(filePostingResponse.status_code) 

            return attachResponse

def post_comment(caseArn, content):
    
    try:
        response = casesclient.create_related_item(
        caseId=caseArn,
        content={
            'comment': {
                'body': content,
                'contentType': 'Text/Plain'
            }
        },
        domainId=CASES_DOMAIN,
        type='Comment'
        )
    except ClientError as e:
        print(f'Error creating case: {e}')
        return False

    return response
