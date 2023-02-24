import boto3
import time
import logging


sqs = boto3.client('sqs')
ec2 = boto3.client('ec2')

ami_id = 'ami-01e547694fca32b28'
min_count = int(0)
max_count = int(20)


current_count = 0
instance_type = 't2.micro'
key_name = 'cc-project-1-key-pair'
security_group_id = 'sg-0ee616cc336f4bcd3'
iam_instance_profile = 'arn:aws:iam::674846823680:instance-profile/EC2-SQS-S3-FullAccess'
instance_name = 'cc-project-1-test-server'
userdata = '#cloud-boothook \n#!/bin/bash \nsudo apt update \nsudo apt install -y python3 \nsudo apt install -y python3-flask \nsudo apt install -y python3-boto3 \nsudo apt install -y tmux \nsudo apt install -y awscli \nmkdir /home/ubuntu/.aws \naws s3 cp s3://cc-project-extra/config /home/ubuntu/.aws/ \naws s3 cp s3://cc-project-extra/config ~/.aws/ \naws s3 cp s3://cc-project-extra/app.py /home/ubuntu/ \nchmod +777 /home/ubuntu/app.py \ntouch /home/ubuntu/log.txt \nchmod -R 777 /home/ubuntu \nsudo -u ubuntu python3 /home/ubuntu/app.py \n'
instance_list = []
scale_in_count=0
request_queue_url: str = (
    "https://sqs.us-east-1.amazonaws.com/674846823680/cc-project-1-request-queue"
)


def controller(logger: logging.Logger) -> None:
    
    instances = ec2.describe_instances( Filters = [{ 'Name': 'instance-state-code', 'Values': [ '0', '16' ] }, { 'Name': 'image-id', 'Values': [ami_id] }] )

    logger.info(instances)

    current_count = 0
    for reservation in instances['Reservations']:
        current_count += len(reservation['Instances'])

    logger.info('Current Count: ' , current_count)

    for x in instances['Reservations']:
        for instance in x['Instances']:
            instance_list.append(instance['InstanceId'])

    logger.info('Instance List: \n', instance_list)

    while True:
        try:
            logger.info('Polling the Request Queue...')
            queue_attr = sqs.get_queue_attributes(QueueUrl = request_queue_url, AttributeNames = ['All'])
            num_visible_msg = int(queue_attr['Attributes']['ApproximateNumberOfMessages'])
            num_invisible_msg = int(queue_attr['Attributes']['ApproximateNumberOfMessagesNotVisible'])
            total_msg = int(num_visible_msg + num_invisible_msg)
            
            logger.info('Total Messages in Queue: ', total_msg)
            logger.info('Total EC2 Instance Running: ', current_count)
            
            if total_msg > current_count and current_count < max_count:
                logger.info('Scaling Out...')
                noOfInstances = min(total_msg-current_count,max_count) - current_count
                instances = ec2.run_instances(ImageId=ami_id, MinCount=noOfInstances, MaxCount=noOfInstances, InstanceType=instance_type, KeyName=key_name, SecurityGroupIds=[security_group_id,], IamInstanceProfile={'Arn' : iam_instance_profile}, TagSpecifications=[{'ResourceType': 'instance', 'Tags' : [{'Key': 'Name', 'Value': 'app-instance'+str(i)},]},], UserData=userdata)
                for i in instances['Instances']:
                    instance_list.append(instance['InstanceId'])
                    logger.info(current_count)
                    current_count += 1
                    
                    
            elif total_msg <= (current_count-1) and current_count > min_count:
                if scale_in_count > 3:
                    logger.info('Scaling In...')
                    for i in range(current_count,total_msg,-1):
                        ec2.terminate_instances(InstanceIds = [instance_list.pop()])
                        current_count -= 1
                        scale_in_count = 0
                        logger.info(current_count)
                else:
                    scale_in_count += 1
                    
            elif current_count<min_count:
                noOfInstances = min_count - current_count
                logger.info('Starting minimum number of instances...')
                instances = ec2.run_instances(ImageId=ami_id, MinCount=noOfInstances, MaxCount=noOfInstances, InstanceType=instance_type, KeyName=key_name, SecurityGroupIds=[security_group_id,], IamInstanceProfile={'Arn' : iam_instance_profile}, TagSpecifications=[{'ResourceType': 'instance', 'Tags' : [{'Key': 'Name', 'Value': 'app-instance'+str(current_count)},]},], UserData=userdata)
                for x in instances['Reservations']:
                    for instance in x['Instances']:
                        instance_list.append(instance['InstanceId'])
                current_count += noOfInstances
                
            else:
                    logger.info('No Scaling Needed...')
            time.sleep(5)
        except Exception as e:
            logger.info(e)
            break

if __name__ == "__main__":
    logging.basicConfig()
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    controller(logger)


