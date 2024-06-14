"""
Description: 
This Python script is part of an application that interacts with AWS DynamoDB to retrieve exchange rates
stored within. The exchange rates are sourced from the European Central Bank and maintained in DynamoDB. 
This script fetches the exchange rates and provides them as a JSON-formatted API response.

This service is designed to be deployed as an AWS Lambda function, which can be triggered by AWS API Gateway 
or other AWS services to provide up-to-date currency exchange information.

Creator: Subhan Malik 
Date: 14/6/24
Email: subhan.sm73@gmail.com

Code Functionality:
- Connects to AWS DynamoDB to retrieve exchange rate data.
- Formats the retrieved data into a structured JSON response.
- Provides both successful responses with data and error handling for cases where data may not be available.
- The script is structured to ensure scalability and reliability, adhering to AWS best practices for serverless applications.

Components:
- DynamoDB: Used for the persistent storage of exchange rate data.
- AWS Lambda: Serves as the compute service to run the script upon triggering.
- AWS API Gateway: Potentially used to trigger this Lambda function in a RESTful API setup.

Usage:
- This script is intended to be deployed as a Lambda function and executed in response to HTTP requests 
  through API Gateway or scheduled events via AWS EventBridge.
"""



import os
import json
import logging
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DynamoDB Configuration
TABLE_NAME = os.environ['DYNAMO_TABLE_NAME']
ENDPOINT_URL = f'http://{os.environ["LOCALSTACK_HOSTNAME"]}:4566' if 'LOCALSTACK_HOSTNAME' in os.environ else None

def handler(event, context):
    """
    Lambda handler to fetch and respond with exchange rates.

    Parameters:
    - event: The event dictionary from AWS Lambda (not used).
    - context: The context object provided by AWS Lambda (not used).

    Returns:
    - dict: A formatted JSON response containing the exchange rates or an error message.
    """
    logger.info('Reading exchange rates from the database.')
    exchange_rates = fetch_exchange_rates_from_db()

    if not exchange_rates:
        logger.warning('No exchange rate data available.')
        return response_with_error("No data available, please try later.")

    response_data = construct_response(exchange_rates)
    return response_with_success(response_data)

def fetch_exchange_rates_from_db():
    """
    Fetches exchange rates from a DynamoDB table.

    Returns:
    - list: A list of dictionaries each containing exchange rate data.
    """
    dynamodb = boto3.resource('dynamodb', endpoint_url=ENDPOINT_URL)
    table = dynamodb.Table(TABLE_NAME)
    response = table.scan()
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    return items

def construct_response(items):
    """
    Constructs a structured response from the items fetched from DynamoDB.

    Parameters:
    - items: A list of dictionaries containing the exchange rate data.

    Returns:
    - dict: A dictionary formatted for JSON response.
    """
    response = {
        'update_date': 'N/A',
        'publish_date': 'N/A',
        'base_currency': 'EUR',
        'exchange_rates': []
    }

    for item in items:
        if item['id'] in ('update_date', 'publish_date'):
            response[item['id']] = item['value']
        else:
            currency_data = {
                'currency': item['id'],
                'rate': item['value'],
                'change': item.get('diff', 'N/A'),
                'change_percentage': item.get('diff_percent', 'N/A')
            }
            response['exchange_rates'].append(currency_data)

    response['exchange_rates'] = sorted(response['exchange_rates'], key=lambda x: x['currency'])
    return response

def response_with_success(data):
    """
    Constructs a successful HTTP response.

    Parameters:
    - data: The data to include in the response body.

    Returns:
    - dict: A response dictionary suitable for AWS Lambda API Gateway.
    """
    return {'statusCode': 200, 'body': json.dumps(data, indent=4)}

def response_with_error(error_message):
    """
    Constructs an error HTTP response.

    Parameters:
    - error_message: The error message to include in the response body.

    Returns:
    - dict: A response dictionary suitable for AWS Lambda API Gateway.
    """
    return {'statusCode': 400, 'body': json.dumps({'error': error_message}, indent=4)}
