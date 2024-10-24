# Amazon Connect Email Cases Integration
This project contains source code and supporting files for supporting email integration as chat conversations. An SES ruleset is created to deliver emails to an S3 bucket, which in turn triggers a Lambda processing function to inject this messages to Amazon Connect in the form of cases. Cases are assigned to customer profiles with the from email address. If no customer profile is found, a new one is created.


## Deployed resources

The project includes a cloud formation template with a Serverless Application Model (SAM) transform to deploy resources as follows:

### AWS Lambda functions

- Receive: Puts received emails on task queue as specified on environment variables.


## Prerequisites.

1. AWS Console Access with administrator account.
2. Amazon Connect Instance already set up with a queue and contact flow for handling chat conversations.
3. Routing profile on Amazon Connect Instance with chat enabled.
4. AWS CLI and SAM tools installed and properly configured with administrator credentials.
5. Verified domain in SES or the posibility to add records to public DNS zone.


## Deploy the solution
1. Clone this repo.

`git clone https://github.com/aws-samples/amazon-connect-email-cases-integration`

2. Build the solution with SAM.

`sam build` 


3. Deploy the solution.

`sam deploy -g`

SAM will ask for the name of the application (use "Connect-Email-Chat" or something similar) as all resources will be grouped under it; a deployment region and a confirmation prompt before deploying resources, enter y. SAM can save this information if you plan un doing changes, answer Y when prompted and accept the default environment and file name for the configuration.

4. If no email entity has been created, browse to the SES console,  and create a verified entity in SES. You'll need to verify domain ownership for the selected entity, this is done by adding entries to DNS resolution. Contact your DNS administrator to facilitate adding these records.

5. In the SES console, browse to the Email receiving section and add any specific filters for receiving email on the created ruleset.

6. Configure the **Amazon Connect Instance ID**  and the **Contact flow** details in the **Receive** function's environment variables.
7. Configure the **Amazon Connect Instance ID** in the **Attach** function's environment variables.
8. Configure the **Amazon Connect Bucket** (BUCKET, use only the bucket name) and the **Amazon Connect Chat storage prefix** (should be in the format: **connect/INSTANCE-NAME/Attachments/chat** ) and the SOURCE_EMAIL (the verified email identity used to send messages from SES) in the **Reply** function's environment variables. 


8. Add the **Reply** function to the Amazon Connect contacflow list.


9. Import the Visual-Mail contact flow for a Visual Step by Step Guide. Modify the associated Lambda function to the function created on the set up process.

10. Create a contact flow to process chat conversations with a Set Event Flow configuring the Default Flow for Agent UI to the one created in the previous process (You can import the sample contact flow file and modify it accordingly.)

## Usage
1. Agents enabled to receive chat conversations with the queue specified on the flow will receive email messages.
2. Responses can be provided on the Visual Step by Step guide.
3. Attachments can be added on the chat conversaton. No message is sent until the associated visual guide is completed.

## Resource deletion
1. From the cloudformation console, select the stack and click on Delete and confirm it by pressing Delete Stack. 
