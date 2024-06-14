import os
import sys
import logging
import urllib.error
import urllib.request
from datetime import datetime
import xml.etree.ElementTree as ET
import boto3

# Constants
DOWNLOAD_URL = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml'
TABLE_NAME = os.environ['DYNAMO_TABLE_NAME']
ENDPOINT_URL = f'http://{os.environ["LOCALSTACK_HOSTNAME"]}:4566' if 'LOCALSTACK_HOSTNAME' in os.environ else None

# Logger Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    """
    Main function to handle the workflow of fetching and updating exchange rates.

    Parameters:
    event: Event data (not used here).
    context: Runtime information (not used here).
    """
    logger.info('Starting to fetch and update exchange rates from the ECB.')
    try:
        date, exchange_rates = fetch_exchange_rates_from_ecb()
        update_exchange_rates_in_db(date, exchange_rates)
        logger.info('Successfully updated exchange rates.')
    except Exception as e:
        logger.exception("Failed to complete the exchange rates update job.")
        raise   # Re-raise the caught exception to let AWS Lambda handle it natively

def parse_exchange_rates_from_xml(doc):
    """
    Parses XML document for exchange rate data.

    Parameters:
    doc (xml.etree.ElementTree.Element): XML document to parse.

    Returns:
    list: A list of dictionaries containing exchange rate data.
    """
    data = []
    for i, cube in enumerate(doc.findall('.//{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube[@time]')):
        daily_data = {
            'date': cube.attrib['time'],
            'rates': {rate.attrib['currency']: rate.attrib['rate'] for rate in cube}
        }
        data.append(daily_data)
        if i == 1:
            break
    return data

def calculate_exchange_rate_differences(data):
    """
    Calculates the differences in exchange rates between two consecutive days.

    Parameters:
    data (list): List of dictionaries containing rate information.

    Returns:
    tuple: A tuple containing the date and a dictionary of exchange rates with differences.
    """
    date, rates_data = data[0]['date'], data[:2]
    latest_rates, previous_rates = rates_data[0]['rates'], rates_data[1]['rates']
    exchange_rates = {}
    for currency, rate in latest_rates.items():
        if currency not in previous_rates:
            continue
        p_rate = float(previous_rates[currency])
        diff = round(float(rate) - p_rate, 4) or 0.0
        diff_percent = round((diff / p_rate) * 100, 4) or 0.0
        diff = f'+{diff}' if diff > 0 else f'{diff}'
        diff_percent = f'+{diff_percent} %' if diff_percent > 0 else f'{diff_percent} %'
        exchange_rates[currency] = {
            'value': rate,
            'diff': diff,
            'diff_percent': diff_percent
        }
    return date, exchange_rates


def fetch_exchange_rates_from_ecb():
    """
    Fetches exchange rates from the European Central Bank's XML feed.

    Returns:
    tuple: A tuple containing the date and a dictionary of exchange rates.
    """
    try:
        with urllib.request.urlopen(DOWNLOAD_URL, timeout=30) as response:
            xml_data = response.read()
        doc = ET.fromstring(xml_data)
        data = parse_exchange_rates_from_xml(doc)
        return calculate_exchange_rate_differences(data)
    except urllib.error.URLError as e:
        logger.error('Failed to download exchange rates data', exc_info=True)
        logger.critical(e)
        sys.exit(1)

def update_exchange_rates_in_db(date, exchange_rates):
    """
    Updates the exchange rates in DynamoDB.

    Parameters:
    date (str): The date of the exchange rates.
    exchange_rates (dict): A dictionary containing the exchange rates to update.
    """
    dynamodb = boto3.resource('dynamodb', endpoint_url=ENDPOINT_URL)
    table = dynamodb.Table(TABLE_NAME)
    with table.batch_writer() as writer:
        for currency, data in exchange_rates.items():
            data['id'] = currency
            writer.put_item(Item=data)
        writer.put_item(Item={'id': 'publish_date', 'value': date})
        writer.put_item(Item={'id': 'update_date', 'value': datetime.utcnow().strftime('%Y-%m-%d')})
