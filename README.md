# slack_jira_integrate
This project is an AWS Lambda function that listens to events from a specific Slack channel and creates Jira issues based on the received messages.<br>
It is usefull for integrating slack channels used to notify alerts or incidents, automatically registering it as a demand (Jira issue) for the team to action or analyze.<br>

<br>

## Features:<br>
* Create Jira issue form message received in specific slack channel<br>
* Checks if a Jira card already exists for the received event, avoiding duplicates<br>
* Replies slack thread with the link to the newly created issue<br>
* Uses first line of the message as the Jira issue's summary. If the first line can't be retrieved (e.g.: message is an image), it uses message timestamp as summary<br>
<br>

## Pre-requisites:<br>
* Jira setup:<br>
  * Jira project configuration: ensure that your Jira project is properly configured with the desired issue type (e.g., "user story"). The issue type you specify must be enabled in the project.<br>
  * Jira API Token: generate a Jira API token for authentication. You can create a token from your Jira account settings<br>
  * User permissions: the user associated with the Jira API token must have permissions to create issues in the specified project.<br>

<br>

* Slack App setup:<br>
  * App creation: create an app and install it in your workspace (you will need admin permission to do that).<br>
  * Slack OAuth Token: generate a token in your app settings.<br>
  * Scopes: OAuth scopes required for this project are chat:write, chat:read and channels:join.<br>
  * Event subscription: set up the Request URL in Slack to point to the AWS API Gateway endpoint that triggers your Lambda function, and subscripte to message.channels event.<br>
<br>
* AWS Lambda setup:<br>
  * Lambda function: create a lambda function using python 3.12 as the runtime. No advanced settings are needed.<br>
  * API gateway: set an API gateway to trigger your function.<br>

## Environment variables:<br>
The following environment variables need to be set for the Lambda function to operate correctly:<br>
* Slack variables:<br>
  * SLACK_TOKEN<br>
  * CHANNEL_ID<br>
  * SLACK_DOMAIN<br>
  * BOT_USER_ID<br>

  <br>

* Jira variables:<br>
  * JIRA_TOKEN<br>
  * JIRA_HOST<br>
  * JIRA_USERNAME<br>
  * JIRA_PROJECT_KEY<br>
  * JIRA_ISSUETYPE_NAME<br>

  <br>

## Dependencies<br>
This function requires external libraries that need to be uploaded in AWS Lambda interface:<br>
* slack_sdl<br>
* pytz<br>
<br>
Install these libraries in a local folder, zip the content, and upload the .zip file in AWS Lambda interface
<br>
<br>
Feel free to reach out if you encounter any issues with this setup!
  



