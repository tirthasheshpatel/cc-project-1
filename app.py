from typing import Any
import subprocess
import sys
import time
import boto3
import base64
import os

sqs = boto3.client("sqs")
s3 = boto3.client("s3")
request_queue_url: str = (
    "https://sqs.us-east-1.amazonaws.com/674846823680/cc-project-1-request-queue"
)
response_queue_url: str = (
    "https://sqs.us-east-1.amazonaws.com/674846823680/cc-project-1-response-queue"
)
input_bucket_name: str = "cc-project-1-input"
output_bucket_name: str = "cc-project-1-output"


def upload_file(file_name: str, bucket: str) -> bool:
    object_name = os.path.basename(file_name)
    s3.upload_file(file_name, bucket, object_name)
    return True


while True:
    try:
        msg = sqs.receive_message(
            QueueUrl=request_queue_url,
            AttributeNames=["All"],
            MessageAttributeNames=["All"],
        )
        bytes = str.encode(msg["Messages"][0]["Body"])

        img_name = msg["Messages"][0]["MessageAttributes"]["ImageName"]["StringValue"]
        img_add: str = f"/home/ubuntu/{img_name}"

        img_bytes = base64.b64decode((bytes))
        with open(img_add, "wb") as file:
            file.write(img_bytes)

        script_dir: str = "/home/ubuntu"
        env = dict(os.environ)

        res: Any = subprocess.call(
            ["python", "image_classification.py", img_add],
            env=env,
            cwd=script_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode != 0:
            print("Image classification script failed with error:\n")
            print(res.stderr.decode("utf-8"))
            sys.exit(1)
        output = res.stdout.decode("utf-8")

        with open(img_add + "-output.txt", "w") as f:
            f.write(output)

        msg_response = sqs.send_message(
            QueueUrl=response_queue_url,
            MessageAttributes={
                "ImageName": {"DataType": "String", "StringValue": img_name}
            },
            MessageBody=output,
        )

        upload_file(img_add, input_bucket_name)
        upload_file(img_add + "-output.txt", output_bucket_name)

        del_responce = sqs.delete_message(
            QueueUrl=request_queue_url,
            ReceiptHandle=msg["Messages"][0]["ReceiptHandle"],
        )

        print(f"{output}")
    except:
        print("Sleep for 5 sec...")
        time.sleep(5)
