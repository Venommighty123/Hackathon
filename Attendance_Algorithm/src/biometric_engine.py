import numpy as np
import tensorflow as tf

class BiometricEngine:
    def __init__(self, model_path=r"Attendance_Algorithm\models\mobilefacenet.tflite"):
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def generate_embedding(self, face_img):
        """
        Input: 112x112 RGB image (numpy array)
        Output: 128-dimensional feature vector (normalized)
        """

        face_img = face_img.astype(np.float32)
        face_img = (face_img - 127.5) / 128.0

        input_data = np.expand_dims(face_img, axis=0)

        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        embedding = self.interpreter.get_tensor(self.output_details[0]['index'])

        norm = np.linalg.norm(embedding)
        normalized_embedding = (embedding / norm).flatten()
        
        return normalized_embedding

    @staticmethod
    def compute_similarity(embedding1, embedding2):
        """
        Calculates the Cosine Similarity between two embeddings.
        Result: 1.0 = Perfect Match, -1.0 = Complete Opposite
        """
        return np.dot(embedding1, embedding2)