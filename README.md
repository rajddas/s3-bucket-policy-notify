# s3-bucket-policy-notify
Notify SNS subscriber on S3 bucket policy changes

# `WatchDog Release Notes`

> ## v1.0.0 (04/10/2021)
> 
> #### First Release features :
> 
> - Send notification to DL on S3 bucket policy changes.
> - Checks bucket policy actions if it has 's3:*' in it.
> - Checks the bucket policy principal to know which role ARN or Account has been given acces.
> - Checks who initiate the bucket policy change.
> - Notifies if the policy change action is success or failed.

> 
> #### Bug Fixes:
> 
> - Removed hardcoding of SNS topic name and others

## Contributors


Rajdeep Das
