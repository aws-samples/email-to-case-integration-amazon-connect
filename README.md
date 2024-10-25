# Amazon Connect Email Cases Integration
This project contains source code and supporting files for supporting email integration as chat conversations. An SES ruleset is created to deliver emails to an S3 bucket, which in turn triggers a Lambda processing function to inject this messages to Amazon Connect in the form of cases. Cases are assigned to customer profiles with the from email address. If no customer profile is found, a new one is created. Responses are sent based on case added comments (One email per commment).


## Deployed resources

The project includes a cloud formation template with a Serverless Application Model (SAM) transform to deploy resources as follows:

### AWS Lambda functions

- Receive: Puts received emails on task queue as specified on environment variables.
- Reply: Sends emails based on case updates.


## Prerequisites.

1. AWS Console Access with administrator account.
2. Amazon Connect Instance already set up with a queue and contact flow for handling chat conversations.
3. Routing profile on Amazon Connect Instance with chat enabled.
4. AWS CLI and SAM tools installed and properly configured with administrator credentials.
5. Verified domain in SES or the posibility to add records to public DNS zone.
6. Amazon Connect Cases domain and Amazon Connect Customer Profiles domain configured.
7. Cases publishing to Eventbridge according to: https://docs.aws.amazon.com/connect/latest/adminguide/case-event-streams-enable.html (No SQS is required)


## Deploy the solution
1. Clone this repo.

`git clone https://github.com/aws-samples/email-to-case-integration-amazon-connect`

2. Build the solution with SAM.

`sam build` 


3. Deploy the solution.

`sam deploy -g`

SAM will ask for the name of the application (use "Connect-Email-Cases" or something similar) as all resources will be grouped under it; the following parameters will also be prompted:
- ConnectInstanceId: Insert the Amazon Connect InstanceID.
- CasesDomain: ID for the associated cases domain.
- CaseTemplate: Template for the case creation.
- CustomerProfilesDomain: Domain for customer profiles. Noticed this is the domain name.
- SourceEmail: Email to be used for email sending. Email reception must be configured separately.

SAM can save this information if you plan un doing changes, answer Y when prompted and accept the default environment and file name for the configuration.

4. If no email entity has been created, browse to the SES console,  and create a verified entity in SES. You'll need to verify domain ownership for the selected entity, this is done by adding entries to DNS resolution. Contact your DNS administrator to facilitate adding these records.

5. In the SES console, browse to the Email receiving section and add any specific filters for receiving email on the created ruleset.

6. On 

## Usage
1. When receiving an email, a matching customer profile will be searched for using the email address.
2. If a customer profile is found, a case will be created under this profile. If no profile is found, one will be created with only the associated email address.
3. Case assignment rules can be defined within Amazon Connect to assign cases.

## Resource deletion
1. From the cloudformation console, select the stack and click on Delete and confirm it by pressing Delete Stack. 
