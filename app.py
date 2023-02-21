import logging
import subprocess
import sys
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


def main(logger: logging.Logger) -> None:
    while True:
        msg = {}
        while "Messages" not in msg:
            logger.info("Checking the request queue for requests.")
            msg = sqs.receive_message(
                QueueUrl=request_queue_url,
                AttributeNames=["All"],
                MessageAttributeNames=["All"],
                WaitTimeSeconds=20,
                MaxNumberOfMessages=1
            )
        bytes = str.encode(msg["Messages"][0]["Body"])

        img_name = msg["Messages"][0]["MessageAttributes"]["ImageName"]["StringValue"]
        logger.info(f"New image `{img_name}` received, now processing.")

        input_path: str = f"/home/ubuntu/{img_name}"
        output_path: str = f"/home/ubuntu/{img_name}-output.txt"

        img_bytes = base64.b64decode((bytes))
        with open(input_path, "wb") as file:
            file.write(img_bytes)

        script_dir: str = "/home/ubuntu"
        env = dict(os.environ)

        res = subprocess.run(
            ["python3", "image_classification.py", img_name],
            env=env,
            cwd=script_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode != 0:
            logger.critical(
                "Image classification script failed with error:", exc_info=True
            )
            sys.exit(1)
        output = res.stdout.decode("utf-8")

        with open(output_path, "w") as f:
            f.write(output)

        logger.info(f"Image `{img_name}` processed.")

        msg_response = sqs.send_message(
            QueueUrl=response_queue_url,
            MessageAttributes={
                "ImageName": {"DataType": "String", "StringValue": img_name}
            },
            MessageBody=output,
        )

        logger.info(f"Send output of `{img_name}` to the response queue.")

        upload_file(input_path, input_bucket_name)
        upload_file(output_path, output_bucket_name)

        logger.info(
            f"Saved `{input_path}` and `{output_path}` in their respective S3 buckets."
        )

        del_responce = sqs.delete_message(
            QueueUrl=request_queue_url,
            ReceiptHandle=msg["Messages"][0]["ReceiptHandle"],
        )

        logger.info(
            f"All tasks completed successfully. Deleted `{img_name}` from the request queue."
        )

        os.remove(input_path)
        os.remove(output_path)


if __name__ == "__main__":
    logging.basicConfig()
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    main(logger)
