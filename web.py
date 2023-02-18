import boto3
import time
import base64
import os
import random
from flask import Flask, request
from werkzeug.utils import secure_filename


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
    return "Hello World! Go to the upload page to upload your images!"


@application.route("/upload", methods=["POST", "GET"])  # type: ignore
def upload() -> None | str:
    if request.method == "POST":
        file = request.files.getlist("myfile")[0]
        if file.filename is None:
            return ""
        filename = secure_filename(file.filename)
        path = os.path.join(application.config["UPLOAD_FOLDER"], filename)
        file.save(path)
        with open(path, "rb") as image2string:
            bytes = base64.b64encode(image2string.read())
        sqs.send_message(
            QueueUrl=request_queue_url,
            MessageAttributes={
                "ImageName": {"DataType": "String", "StringValue": filename}
            },
            MessageBody=bytes.decode("ascii"),
        )

        while True:
            try:
                queue_attr = sqs.get_queue_attributes(
                    QueueUrl=response_queue_url, AttributeNames=["All"]
                )
                num_visible_msg = int(
                    queue_attr["Attributes"]["ApproximateNumberOfMessages"]
                )
                print(f"Number of visible messages: {num_visible_msg}")
                if num_visible_msg > 0:
                    msg = sqs.receive_message(
                        QueueUrl=response_queue_url,
                        AttributeNames=["All"],
                        MessageAttributeNames=["All"],
                    )
                    body = msg["Messages"][0]["Body"]
                    filename, result = body.split(",")
                    print(f"Received `{body}`")
                    if filename != file.filename:
                        continue
                    sqs.delete_message(
                        QueueUrl=response_queue_url,
                        ReceiptHandle=msg["Messages"][0]["ReceiptHandle"],
                    )
                    print("Returning response")
                    return f"Result for file '{filename}': {result}"
                else:
                    time.sleep(random.random() * 3 + 1)
                    continue
            except Exception as e:
                print("Exception Occured...")
                print(e)
                time.sleep(random.random() * 3 + 1)


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=8080)
