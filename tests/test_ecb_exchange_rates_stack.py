"""
Description: Unit tests for validating the ECB Exchange Rates CDK stack.
Ensures essential resources such as DynamoDB tables, Lambda functions, and API Gateway are correctly configured.

Creator: Subhan Malik 
Date: 6/14/24
Email: subhan.sm73@gmail.com
"""

import aws_cdk as core
import aws_cdk.assertions as assertions
from app import ECBExchangeRatesStack

def create_stack():
    """Creates and returns an instance of ECBExchangeRatesStack."""
    app = core.App()
    return ECBExchangeRatesStack(app, 'ecb-exchange-rates')

def test_dynamodb_table_created():
    """Verify if the DynamoDB table is correctly created with proper schema and deletion policy."""
    stack = create_stack()
    template = assertions.Template.from_stack(stack)
    assert_dynamodb_table_properties(template)
    assert_dynamodb_table_deletion_policy(template)

def assert_dynamodb_table_properties(template):
    """Asserts the DynamoDB table properties are as expected."""
    template.has_resource_properties('AWS::DynamoDB::Table', {
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'id', 'AttributeType': 'S'}]
    })

def assert_dynamodb_table_deletion_policy(template):
    """Ensures that the DynamoDB table has the correct deletion policy."""
    template.has_resource('AWS::DynamoDB::Table', {'DeletionPolicy': 'Delete'})

def test_update_lambda_created():
    """Tests if the update lambda function is created with the correct configuration."""
    stack = create_stack()
    template = assertions.Template.from_stack(stack)
    assert_lambda_properties(template, 'update_ecb_exchange_rates.handler', 360)

def test_read_lambda_created():
    """Tests if the read lambda function is created with the correct configuration."""
    stack = create_stack()
    template = assertions.Template.from_stack(stack)
    assert_lambda_properties(template, 'get_ecb_exchange_rates.handler', 60)

def assert_lambda_properties(template, handler, timeout):
    """Asserts lambda function properties including handler, runtime, and environment variables."""
    template.has_resource_properties('AWS::Lambda::Function', {
        'Handler': handler,
        'Runtime': 'python3.8',
        'Timeout': timeout,
        'Environment': {'Variables': {'DYNAMO_TABLE_NAME': {}}}
    })

def test_rest_api_created():
    """Tests if the REST API is created and configured correctly."""
    stack = create_stack()
    template = assertions.Template.from_stack(stack)
    assert_rest_api_properties(template)

def assert_rest_api_properties(template):
    """Asserts properties of the REST API components."""
    template.has_resource_properties('AWS::ApiGateway::RestApi', {'Name': 'api-ecb-exchange-rates'})
    template.has_resource_properties('AWS::ApiGateway::Resource', {'PathPart': 'getecbexchangerates'})
    template.has_resource_properties('AWS::ApiGateway::Method', {'HttpMethod': 'GET'})