import boto3
import logging
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Retrieve environment variables
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
DYNAMODB_TABLE_NAME = os.environ['DYNAMODB_TABLE_NAME']
FINE_AMOUNT_THRESHOLD = int(os.environ.get('FINE_AMOUNT_THRESHOLD', 500))

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    rekognition = boto3.client('rekognition')
    sns = boto3.client('sns')

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    logger.info(f'Bucket: {bucket}, Key: {key}')

    response = s3.get_object(Bucket=bucket, Key=key)
    image_bytes = response['Body'].read()

    response = rekognition.detect_text(Image={'Bytes': image_bytes})

    license_plate = extract_license_plate(response)
    if license_plate:
        logger.info(f'Detected license plate: {license_plate}')

        fine_info = {
            'license_plate': license_plate,
            'fine_amount': calculate_fine()
        }
        logger.info(f'Fine info: {fine_info}')
        send_notification(fine_info, sns)
    else:
        logger.warning('No license plate detected in the image.')

    return {
        'statusCode': 200,
        'body': 'License plate processed'
    }

def extract_license_plate(rekognition_response):
    for text_detection in rekognition_response['TextDetections']:
        detected_text = text_detection['DetectedText']
        if is_license_plate(detected_text):
            return detected_text
    return None

def is_license_plate(text):
    # Simple validation, customize as needed
    return len(text) >= 5 and len(text) <= 10

def calculate_fine():
    return FINE_AMOUNT_THRESHOLD

def send_notification(fine_info, sns):
    message = (
        f"Your vehicle with license plate {fine_info['license_plate']} was detected overspeeding. "
        f"Fine amount: ${fine_info['fine_amount']}."
    )
    logger.info(f'Sending message: {message}')
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=message
    )
