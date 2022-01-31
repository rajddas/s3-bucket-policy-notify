#######################################################################################
#                                                                                     #
#  Description           :  Used to trigger SNS notification on S3 bucket policy      #
#                           changes                                                   #
#                                                                                     #
#######################################################################################

################################ Import Modules #######################################

import json
import boto3
import os
import logging
import time
from dateutil import tz
from datetime import datetime

################################## Loading logger ###################################

def load_log_config():
    """
    # Basic config. Replace with your own logging config if required
    :return: object for basic logging
    """
    global logger

    LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(format=LOG_FORMAT, datefmt=DATETIME_FORMAT)
    logger = logging.getLogger("LAMBDA_LOG")
    
    logger.setLevel(logging.DEBUG)

############################## Initializing Clients ###################################

s3 = boto3.client('s3')
sns_client = boto3.client('sns')

####################### check for AWS principal ARNs in Policy ########################

def check_for_iam_principals(bucket_policy):
    '''
    Usage   : Checks for IAM principals in policy.
    Args    : bucket policy
    Returns : principal arns string (comma seperated)
    Raises  : Exception while running this function.
    '''

    try:
        logger.info('Checking for IAM principals in policy')
        statement_count = len(bucket_policy['Statement'])
        principals = []
        principal_string = ''
        if statement_count != 0:
            for i in range(statement_count):
                if ("AWS" in bucket_policy['Statement'][i]['Principal']):
                    if (type(bucket_policy['Statement'][i]['Principal']['AWS']) is str):
                        principals.append(bucket_policy['Statement'][i]['Principal']['AWS'])
                    else:
                        principals = principals + bucket_policy['Statement'][i]['Principal']['AWS']
                else:
                    continue

            logger.info('All IAM principals in policy : ')
            logger.info(principals)
            principal_string = ", ".join(principals)
                 
        else:
            logger.info('***** The bucket policy is invalid.')
        
        return principal_string

    except Exception as e:
        logger.error('***** ERROR: while checking for principals in bucket policy : '+str(e))
        raise Exception('Error while checking for principals in bucket policy. Reason : ' +str(e))

######################## check if over permissive actions are there ############################

def check_if_over_permissive_action(bucket_policy):
    '''
    Usage   : Checks if overpermissive actions were used in bucket policy ex. s3:*.
    Args    : bucket policy
    Returns : True/False
    Raises  : Exception while running this function.
    '''

    try:
        logger.info('Checking for over permissive actions in policy')
        statement_count = len(bucket_policy['Statement'])
        actions = []
        if statement_count != 0:
            for i in range(statement_count):
                if (type(bucket_policy['Statement'][i]['Action']) is str):
                    actions.append(bucket_policy['Statement'][i]['Action'])
                else:
                    actions = actions + bucket_policy['Statement'][i]['Action']
            logger.info('All Actions in policy : ')
            logger.info(actions)
            if ('s3:*' in actions):
                return True
            else:
                return False
                
        else:
            logger.info('***** The bucket policy is invalid.')


    except Exception as e:
        logger.error('***** ERROR: while checking over permissive bucket policy : '+str(e))
        raise Exception('Error while checking over permissive bucket policy. Reason : ' +str(e))

############################ Sending Notification ##################################

def send_notification(subject,email_body,sns_arn):

    """
    Usage   : Sending SNS notification
    Args    : SNS Email Body
    Returns : Nothing
    Raises  : Exception While Sending SNS notification.
    
    """
    try:
        
        logger.info('Sending Notification to ' +sns_arn)

        sns_client.publish(TopicArn =sns_arn,Subject=subject,Message=email_body)

        logger.info('Notification Sent')

    except Exception as e:
        logger.error('***** ERROR : Unexpected ERROR while Sending SNS Notification : '+str(e))
        raise Exception('ERROR : While Sending SNS Notification with ERROR : ' +str(e))


########################## Create SNS Email Body ###################################

def create_sns_body(sns_parm,account,region_name):

    """
     Usage   : Creating SNS Email Body
     Args    : sns parameters dict
     Returns : SNS Email Body
     Raises  : Exception While Creating SNS Email Body.
     """
    try:
        event_api_name = sns_parm['event_api_name']
        event_source   = sns_parm['event_source']
        event_time     = sns_parm['event_time']
        identity       = sns_parm['identity']

        email_body = ''
        subject    = ''
        if ('s3.amazonaws.com' in event_source):
            bucket_name         = sns_parm['bucket_name']
            if ('PutBucketPolicy' in event_api_name):
                if ('error_code' not in sns_parm):
                    over_permissive_policy = sns_parm['over_permissive_policy']
                    principal_arn_string   = sns_parm['principal_arn_string']
                    subject    = f'[{account} WatchDog] {event_api_name} on S3 Bucket : {bucket_name}'
                    email_body = 'Hi Team, \n\nPlease find bucket configuration change details below :\n\nPolicy Change Status  :  Succeeded\nAccount  :  '+account+'\nRegion  :   '+region_name+'\nBucket Name   :   '+bucket_name+'\nChange Initiated By : '+identity+'\nAPI Call Made  :  '+event_api_name+'\nEvent Initiation Time(UTC)  :  '+str(event_time)+'\nOver Permissive Actions on Policy (s3:*)   :    '+over_permissive_policy+'\nRoles/Accounts Given Access   :  '+principal_arn_string+'\n\nThanks!'
                else:
                    error_code     = sns_parm['error_code']
                    error_message  = sns_parm['error_message']
                    subject    = f'[{account} WatchDog] {event_api_name} on S3 Bucket : {bucket_name}'
                    email_body = 'Hi Team, \n\nPlease find bucket configuration change details below :\n\nPolicy Change Status   :   Failed\nAccount   :    '+account+'\nRegion  :    '+region_name+'\nBucket Name   :    '+bucket_name+'\nChange Initiated By   :   '+identity+'\nAPI Call Made    :    '+event_api_name+'\nEvent Time(UTC)     :    '+str(event_time)+'\nError Code   :    '+error_code+'\nError Message    :    '+error_message+'\n\nThanks!'
        
        return subject, email_body

    except Exception as e:
        logger.error('***** ERROR : Unexpected ERROR while Creating SNS Email Body : ' +str(e))
        raise Exception('ERROR : While Creating SNS Email Body with ERROR : ' +str(e))

################################## Main Lambda Handler ###############################

def lambda_handler(event, context):
    
    '''
    Usage   : Main Function called by Lambda
    Args    : Event and Context - Default
    Returns : Dictionary with function execution status.
    Raises  : Exceptions sent by the other functions
    '''
    

    try:
        load_log_config()
        logger.info('Function Execution is Starting ....')
        logger.info('Whole Event Received from Cloudwatch :')
        logger.info(json.dumps(event))
    

        region_name  = os.environ['AWS_REGION']
        sns_arn      = os.environ['SNS_ARN']
        account      = context.invoked_function_arn.split(":")[4]
        utc          = datetime.utcnow()
        event_time   = utc.replace(tzinfo=tz.gettz('UTC'))
     
        
        # Getting required details from the cloudwatch event.
        
        event_detail   = event['detail']
        event_source   = event_detail['eventSource']
        event_api_name = event_detail['eventName']
        identity       = event_detail['userIdentity']['arn'].split(":")[-1]

        if (event_source == 's3.amazonaws.com'):
            bucket_name  =  event_detail['requestParameters']['bucketName']
            if (event_api_name=='PutBucketPolicy'):
                if ("errorCode" in event_detail):
                    logger.info('Bucket Policy Apply Failed to s3://'+bucket_name+' because of : '+event_detail['errorMessage'])
                    sns_parm = {
                        "event_api_name" : event_api_name,
                        "event_source"   : event_source,
                        "event_time"     : event_time,
                        "identity"       : identity,
                        "bucket_name"    : bucket_name,
                        "error_code"     : event_detail['errorCode'],
                        "error_message"  : event_detail['errorMessage']
                    }
                    subject,email_body = create_sns_body(sns_parm,account,region_name)
                    send_notification(subject,email_body,sns_arn)
                    logger.info('Function execution complete.')
                else:
                    bucket_policy = event_detail['requestParameters']['bucketPolicy']
                    principal_arn_string = check_for_iam_principals(bucket_policy)
                    if check_if_over_permissive_action(bucket_policy):
                        sns_parm = {
                        "event_api_name" : event_api_name,
                        "event_source"   : event_source,
                        "event_time"     : event_time,
                        "identity"       : identity,
                        "bucket_name"    : bucket_name,
                        "over_permissive_policy" : "True",
                        "principal_arn_string" : principal_arn_string,
                        "bucket_policy" : event_detail['requestParameters']['bucketPolicy']
                        }
                        subject,email_body = create_sns_body(sns_parm,account,region_name)
                        send_notification(subject,email_body,sns_arn)
                        logger.info('Function execution complete.')
                    else:
                        sns_parm = {
                        "event_api_name" : event_api_name,
                        "event_source"   : event_source,
                        "event_time"     : event_time,
                        "identity"       : identity,
                        "bucket_name"    : bucket_name,
                        "over_permissive_policy" : "False",
                        "principal_arn_string" : principal_arn_string,
                        "bucket_policy" : event_detail['requestParameters']['bucketPolicy']
                        }
                        subject,email_body = create_sns_body(sns_parm,account,region_name)
                        send_notification(subject,email_body,sns_arn)
                        logger.info('Function execution complete.')

        return {
            'statusCode': 200,
            'body': 'Executed Successfully'
        }  

    except Exception as e:
        logger.error('***** ERROR: Unexpected ERROR in Lambda Execution :' +str(e))
        raise e
