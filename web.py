import logging
import boto3
import time
import base64
import os
import random
from flask import Flask, request
from werkzeug.utils import secure_filename

logging.basicConfig()
logger = logging.getLogger("web")
logger.setLevel(logging.INFO)

UPLOAD_FOLDER: str = "./data"
application = Flask(__name__)
application.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

sqs = boto3.client("sqs")

request_queue_url: str = (
    "https://sqs.us-east-1.amazonaws.com/674846823680/cc-project-1-request-queue"
)
response_queue_url: str = (
    "https://sqs.us-east-1.amazonaws.com/674846823680/cc-project-1-response-queue"
)


@application.route("/")
def hello_world() -> str:
    logger.info("Home page accessed.")
    return "Hello World! Go to the upload page to upload your images!"


@application.route("/upload", methods=["POST", "GET"])  # type: ignore
def upload() -> None | str:
    if request.method == "POST":
        file = request.files.getlist("myfile")[0]
        logger.info(f"Received file `{file.filename}`.")
        if file.filename is None or not os.path.basename(file.filename).lower().endswith('jpeg'):
            logger.warning("Invalid file received!")
            return "Invalid file received!"
        filename = secure_filename(file.filename)
        path = os.path.join(application.config["UPLOAD_FOLDER"], filename)
        file.save(path)  # Upload the image
        logger.info(f"Uploaded image `{file.filename}`.")
        with open(path, "rb") as image2string:
            bytes = base64.b64encode(image2string.read())
        sqs.send_message(
            QueueUrl=request_queue_url,
            MessageAttributes={
                "ImageName": {"DataType": "String", "StringValue": os.path.basename(filename)}
            },
            MessageBody=bytes.decode("ascii"),
        )
        logger.info(f"Sent image `{os.path.basename(filename)}` to the request queue.")

        logger.info("Now waiting for response.")
        while True:
            msg = {}
            while 'Messages' not in msg:
                logger.info(f"Checking the response queue for a response.")
                msg = sqs.receive_message(
                    QueueUrl=response_queue_url,
                    AttributeNames=["All"],
                    MessageAttributeNames=["All"],
                    WaitTimeSeconds=123,
                    MaxNumberOfMessages=1
                )
            body = msg["Messages"][0]["Body"]
            filename, result = body.split(",")
            if filename == file.filename:
                logger.info(f"Response found: `{body}`")
                sqs.delete_message(
                    QueueUrl=response_queue_url,
                    ReceiptHandle=msg["Messages"][0]["ReceiptHandle"],
                )
                logger.info("Deleted response from queue. Returning response.")
                return f"Result for file '{filename}': {result}"


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=8080)
