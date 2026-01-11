import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np
from .utils.image_utils import align_face, validate_face_geometry

def process_captured_image(image_path, model_path=r'Attendance_Algorithm\models\blaze_face_short_range.tflite'):

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceDetectorOptions(base_options=base_options)
    detector = vision.FaceDetector.create_from_options(options)

    image = cv2.imread(image_path)
    if image is None:
        return {"status": "error", "message": "File not found"}
    
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

    detection_result = detector.detect(mp_image)

    if not detection_result.detections:
        return {"status": "failed", "message": "No face detected. Look directly at camera."}

    keypoints = detection_result.detections[0].keypoints

    is_valid, angle, msg = validate_face_geometry(image, keypoints)
    
    if not is_valid:
        return {
            "status": "update_required",
            "message": msg,
            "angle": angle
        }

    aligned_img = align_face(image, keypoints)

    bbox = detection_result.detections[0].bounding_box
    x, y, w, h = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height

    pad_w, pad_h = int(w * 0.1), int(h * 0.1)
    face_crop = aligned_img[max(0, y-pad_h):y+h+pad_h, max(0, x-pad_w):x+w+pad_w]

    face_final = cv2.resize(face_crop, (112, 112))

    return {
        "status": "success",
        "processed_face": face_final,
        "message": "Face detected, aligned, and cropped to 112x112."
    }