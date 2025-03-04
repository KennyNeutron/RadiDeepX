from flask import Flask, render_template, request, jsonify
import os
import cv2
import numpy as np
from werkzeug.utils import secure_filename
from inference_sdk import InferenceHTTPClient

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["PROCESSED_FOLDER"] = "static/processed"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg"}


CLIENT = InferenceHTTPClient(api_url="xxxx", api_key="xxxx")

MODEL_ID = "xxxxx"


CLASS_COLORS = {
    "leftheart": (50, 205, 50),
    "rightheart": (148, 0, 211),
    "thorax": (255, 0, 0),
}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part"})
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        result = CLIENT.infer(filepath, model_id=MODEL_ID)

        processed_path = os.path.join(app.config["PROCESSED_FOLDER"], filename)
        image = cv2.imread(filepath)

        for prediction in result.get("predictions", []):
            x, y, width, height = (
                int(prediction["x"]),
                int(prediction["y"]),
                int(prediction["width"]),
                int(prediction["height"]),
            )
            confidence = prediction["confidence"]
            class_name = prediction["class"]

            color = CLASS_COLORS.get(class_name, (0, 255, 0))

            start_point = (x - width // 2, y - height // 2)
            end_point = (x + width // 2, y + height // 2)
            cv2.rectangle(image, start_point, end_point, color, 1)

            text = f"{class_name}: {confidence:.2f}"
            font_scale = 0.6
            thickness = 1
            text_size = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
            )[0]
            text_x = start_point[0]
            text_y = start_point[1] - 5

            cv2.rectangle(
                image,
                (text_x, text_y - text_size[1] - 5),
                (text_x + text_size[0] + 5, text_y + 5),
                color,
                -1,
            )
            cv2.putText(
                image,
                text,
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                thickness,
            )

        cv2.imwrite(processed_path, image)

        return render_template(
            "index.html",
            image_url=filepath,
            processed_url=processed_path,
            result=result,
        )
    return jsonify({"error": "Invalid file type"})


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)
    app.run(debug=True)
