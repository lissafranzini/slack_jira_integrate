import os
import http.client
import base64
import json
import logging
from datetime import datetime
import pytz
import urllib.parse
from slack_sdk import WebClient  
from slack_sdk.errors import SlackApiError
import time

# log config
logging.basicConfig(level=logging.INFO)

# Slack config
slack_token = os.environ.get('SLACK_TOKEN')
channel_id = os.environ['CHANNEL_ID']
slack_client = WebClient(token=slack_token)

# Jira config
jira_api_url = '/rest/api/2/issue'
jira_host = 'yout.host.net'
jira_username = 'your.user@mail.com.br'
jira_token = os.environ.get('JIRA_TOKEN')

# Auth header
auth_string = f'{jira_username}:{jira_token}'
auth_string_encoded = base64.b64encode(auth_string.encode()).decode()

# Calls Jira rest api to create card
def create_jira_issue(summary, description):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth_string_encoded}'
    }
    payload = {
        'fields': {
            'project': {'key': 'KEY'},
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'user story'}, #config this to any issuetype that is avaiable on your Jira Project
        }
    }
    
    try:
        conn = http.client.HTTPSConnection(jira_host)
        conn.request("POST", jira_api_url, json.dumps(payload), headers)
        response = conn.getresponse()
        response_data = response.read().decode()
        conn.close()
        
        if response.status == 201:
            response_data_json = json.loads(response_data)
            issue_key = response_data_json['key']
            issue_link = f'https://{jira_host}/browse/{issue_key}'
            logging.info('An issue was created!')
            return response.status, issue_link
        else:
            logging.error('Error while creating Jira issue: %s', response_data)
            return response.status, response_data
    except Exception as e:
        logging.error('Error while creating Jira issue: %s', str(e))
        return 500, str(e)

# Posts message on slack thread containing link to created issue
def send_slack_message(message, thread_ts=None, retries=3, delay=2):
   #Retry loop
    for attempt in range(retries):
        try:
            response = slack_client.chat_postMessage(channel=channel_id, text=message, thread_ts=thread_ts)
            
            logging.info('Message successfully sent')
            return response.status_code, response.data
            
        except SlackApiError as e:
            logging.error('Error while sending message: %s', e.response['error'])
            if attempt < retries - 1:
                time.sleep(delay) 
            else:
                return e.response.status_code, e.response['error']
        except Exception as e:
            logging.error('Error while sending message: %s', str(e))
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return 500, str(e)
            

# Checks if there is already a card created for a specifc thread, avoiding duplicates        
def check_existing_card(slack_thread_link):
    query = f'project = KEY AND text ~ "{slack_thread_link}"'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth_string_encoded}'
    }
    endpoint = f'/rest/api/2/search?jql={urllib.parse.quote(query)}'
    
    try:
        conn = http.client.HTTPSConnection(jira_host)
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode()
        conn.close()
        
        if response.status == 200:
            response_data_json = json.loads(response_data)
            issues = response_data_json['issues']
            if issues:
                return True
            else:
                return False
        else:
            logging.error('Error while getting Jira issue: %s', response_data)
            return False
    except Exception as e:
        logging.error('Error while getting Jira issue: %s', str(e))
        return False
    
# Parses event and returns body
def parse_event(event):
    try:
        body = json.loads(event['body'])
        logging.info('body: %s', body)
        return body
    except json.JSONDecodeError as e:
        logging.error('Error while decoding JSON: %s', str(e))
        return None
    
# Validates incoming events, including slack challenge
def validate_event(body):
    if 'challenge' in body:
        return{'statusCode': 200, 'body': json.dumps({'challenge': body['challenge']})}
    
    if 'event' in body and 'text' in body['event']:
        return None #Valid event, no error
    else:
        logging.error('Event type not valid or lack of payload')
        return {'statusCode': 400, 'body': json.dumps({'error': 'Event type not valid or lack of payload'})}

# Processes event, getting information about the received message    
def process_event(body):
    bot_id = os.environ['BOT_USER_ID']
    sender_id = body['event']['user']
    thread_ts = body['event'].get('thread_ts', body['event'].get('ts'))
    permalink = f"https://domain.slack.com/archives/{channel_id}/p{thread_ts.replace('.', '')}"

    if sender_id != bot_id and 'thread_ts' not in body['event']:
        description = f"{body['event']['text']} \nlink to slack thread: {permalink}"

        try:
            message_timestamp = datetime.fromtimestamp(float(thread_ts))
            tz_brazil = pytz.timezone('America/Sao_Paulo')
            message_timestamp_brazil = message_timestamp.astimezone(tz_brazil)
            formatted_timestamp = message_timestamp_brazil.strftime("%d/%m - %H:%M")
        except (ValueError, TypeError) as e:
            logging.error('Error while converting timestamp to brazilian time: %s', str(e))
            return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid timestamp'})}

        summary = extract_summary(body['event']['text'], formatted_timestamp)
        card_exists = check_existing_card(permalink)

        if card_exists:
            logging.info('Issue corresponding to thread already exists on Jira')
            return {'statusCode': 200, 'body': json.dumps({'message':'Issue corresponding to thread already exists on Jira'})}
        else:
            status, response_data = create_jira_issue(summary, description)
            if status == 201:
                message = f'Incoming message. A Jira issue was created: {response_data}'
                slack_status, response_data_slack = send_slack_message(message, thread_ts)
                slack_response = response_data_slack if isinstance(response_data_slack, str) else response_data_slack.get('message', 'No message')
                return {
                    'statusCode':200,
                    'body': json.dumps({
                        'message':'Message processed and issue created',
                        'link':response_data,
                        'slack return': slack_response
                    })
                }
            else:
                logging.error('Error while creating Jira issue: %s', response_data)
                return {'statusCode': 400, 'body': json.dumps({'error':'Error while creating Jira issue', 'jira_response':response_data})}
    else:
        logging.error('Invalid sender or event lacks thread_ts')
        return{'statusCode': 400, 'body': json.dumps({'error':'Invalid sender or event lacks thread_ts'})}
    
def extract_summary(text, formatted_timestamp):
    lines = text.split('\n')
    if lines and lines[0]:
        return f'Message - {lines[0].strip()}'
    return f'Message - {formatted_timestamp}'
   

def lambda_handler(event, context):
    logging.info('Incoming event: %s', event)

    if 'body' in event:
        body = parse_event(event)
        if body is None:
            return {'statusCode': 400, 'body': json.dumps({'error': 'invalid JSON'})}
        
        validation_response = validate_event(body)
        if validation_response:
            return validation_response
        
        return process_event(body)
    
    else:
        logging.error('Requisition lacks body')
        return{'statusCode': 400, 'body': json.dumps({'error':'Requisition lacks body'})} 
