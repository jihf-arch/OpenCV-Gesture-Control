import cv2

class Camera:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def read(self):
        ret, frame = self.cap.read()
        if ret:
            return cv2.flip(frame, 1)  # 镜像，更自然
        return None

    def release(self):
        self.cap.release()