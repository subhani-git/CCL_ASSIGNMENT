#!/usr/bin/env python3

import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    Stack,
    triggers,
    Duration,
    RemovalPolicy,
    aws_logs as logs,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_apigateway as apigateway,
    aws_events_targets as events_targets
)

class ECBExchangeRatesStack(Stack):
    """Stack for managing ECB Exchange Rates, including DynamoDB, Lambda Functions, and API Gateway."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        exchange_rates_table = self.create_dynamodb_table()

        update_lambda = self.create_lambda_function('update-ecb-exchange-rates','update_ecb_exchange_rates.handler', 6, './updatelambda')
        read_lambda = self.create_lambda_function(
            'get-ecb-exchange-rates', 
            'get_ecb_exchange_rates.handler', 
            1, './getlambda'
        )

        update_lambda.add_environment('DYNAMO_TABLE_NAME', exchange_rates_table.table_name)
        read_lambda.add_environment('DYNAMO_TABLE_NAME', exchange_rates_table.table_name)

        exchange_rates_table.grant_read_write_data(update_lambda)
        exchange_rates_table.grant_read_data(read_lambda)

        self.schedule_lambda_execution(update_lambda)
        self.create_rest_api(read_lambda)
        self.create_initial_data_trigger(exchange_rates_table, update_lambda)


    def create_lambda_function(self, id: str, handler: str, timeout_minutes: int, codepath: str):
        """Creates a Lambda function for handling exchange rates."""
        return _lambda.Function(
            self, id,
            runtime=_lambda.Runtime.PYTHON_3_8,
            code=_lambda.Code.from_asset(codepath),
            handler=handler,
            timeout=Duration.minutes(timeout_minutes),
            log_retention=logs.RetentionDays.ONE_DAY
        )
    
    

    def create_dynamodb_table(self):
        """Creates a DynamoDB table for storing exchange rates."""
        return dynamodb.Table(
            self, 'table-ecb-exchange-rates',
            partition_key=dynamodb.Attribute(name='id', type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

    def create_rest_api(self, lambda_function):
        """Creates a REST API for accessing exchange rates."""
        api = apigateway.LambdaRestApi(self, 'api-ecb-exchange-rates', handler=lambda_function, proxy=False)
        api.root.add_resource('getecbexchangerates').add_method('GET')


    def schedule_lambda_execution(self, lambda_function):
        """Schedules daily execution of the Lambda function."""
        rule = events.Rule(
            self, "ecb-exchange-rates-update-scheduler",
            schedule=events.Schedule.cron(hour='17', minute='0'),
            targets=[events_targets.LambdaFunction(lambda_function)]
        )

    def create_initial_data_trigger(self, exchange_rates_table, update_lambda):
        init_trigger = triggers.TriggerFunction(self, 'init-ecb-echange-rates',
                                                execute_after=[exchange_rates_table, update_lambda],
                                                runtime=_lambda.Runtime.PYTHON_3_8,
                                                code=_lambda.Code.from_asset('./updatelambda'),
                                                handler='update_ecb_exchange_rates.handler',
                                                timeout=Duration.minutes(5),
                                                log_retention=logs.RetentionDays.ONE_DAY,
                                                execute_on_handler_change=False)
        init_trigger.add_environment('DYNAMO_TABLE_NAME', exchange_rates_table.table_name)
        exchange_rates_table.grant_read_write_data(init_trigger)

# Main Application
app = cdk.App()
ECBExchangeRatesStack(app, 'ecb-exchange-rates')
app.synth()
