import cv2
import numpy as np

def align_face(image, landmarks):
    """
    Standardizes face orientation based on eye positions.
    landmarks: list of mediapipe keypoints
    """

    ih, iw, _ = image.shape
    
    right_eye = (int(landmarks[0].x * iw), int(landmarks[0].y * ih))
    left_eye = (int(landmarks[1].x * iw), int(landmarks[1].y * ih))

    dY = left_eye[1] - right_eye[1]
    dX = left_eye[0] - right_eye[0]
    angle = np.degrees(np.arctan2(dY, dX))

    eye_center = (
        int((left_eye[0] + right_eye[0]) // 2),
        int((left_eye[1] + right_eye[1]) // 2)
    )

    M = cv2.getRotationMatrix2D(eye_center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (iw, ih), flags=cv2.INTER_CUBIC)
    
    return rotated

def validate_face_geometry(image, keypoints):
    """
    Checks if the face is tilted beyond acceptable HR standards.
    Returns: (is_valid, angle, message)
    """
    ih, iw, _ = image.shape

    right_eye = (int(keypoints[0].x * iw), int(keypoints[0].y * ih))
    left_eye = (int(keypoints[1].x * iw), int(keypoints[1].y * ih))

    dY = left_eye[1] - right_eye[1]
    dX = left_eye[0] - right_eye[0]
    angle = np.degrees(np.arctan2(dY, dX))

    if abs(angle) > 20:
        return False, angle, f"Face tilted by {abs(angle):.1f}°. Please hold phone straight."
    
    return True, angle, "Orientation correct."