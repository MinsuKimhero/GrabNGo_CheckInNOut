import sys
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSlot, QTimer, QDate,Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QApplication,QMainWindow
import os
from db_connection import DB_Connection
import numpy as np
from Face_Recognition import pre_trained_facenet
import cv2
from facenet_pytorch import MTCNN
import tensorflow.compat.v1 as tf
import time

class Check_In_Window(QMainWindow):
    def __init__(self):
        super(Check_In_Window, self).__init__()
        loadUi("Check_In_Window.ui", self)
        self.mtcnn = MTCNN(select_largest=True, device='cuda')
        # some constants kept as default from facenet
        self.input_image_size = 160

        self.sess = tf.compat.v1.Session(config=tf.compat.v1.ConfigProto(log_device_placement=True))
        pre_trained_facenet.load_model('model/20170512-110547.pb')
        self.images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
        self.embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
        self.phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
        self.embedding_size = self.embeddings.get_shape()[1]
        self.startVideo('0')

    def startVideo(self, camera_name):
        """
        :param camera_name: link of camera or usb camera
        :return:
        """
        if len(camera_name) == 1:
        	self.capture = cv2.VideoCapture(int(camera_name))
        else:
        	self.capture = cv2.VideoCapture(camera_name)
        self.timer = QTimer(self)  # Create Timer
        # path = './Face_Recognition/images'
        path = '/home/ftpuser/ftp/files/'
        if not os.path.exists(path):
            os.mkdir(path)
        # known face encoding and known face name list
        self.images = []
        self.class_names = []
        self.faces = []

        attendance_list = os.listdir(path)
        self.attendance_num = len(attendance_list)
        for cl in attendance_list:
            cur_img = cv2.imread(f'{path}/{cl}')
            print(cur_img)
            self.images.append(cur_img)
            # print('image',cur_img)
            # cur_img = cv2.resize(cur_img, (504,378))
            faces_detected = 0
            start = time.time()
            # result = self.detector.detect_faces(cur_img)
            box = self.mtcnn.detect(cur_img,True)

            faces_detected += len(box)
            print(box)
            print(
                f'Frames per second: {(time.time() - start):.3f},',
                f'faces detected: {faces_detected}\r'
            )
            face = self.getFace(cur_img, box)
            self.faces.append(face)
            self.class_names.append(os.path.splitext(cl)[0])

        self.timer.timeout.connect(self.update_frame)  # Connect timeout to the output function
        self.timer.start(10)  # emit the timeout() signal at x=10ms

    def face_rec_(self, frame):
        """
        :param frame: frame from camera
        :param encode_list_known: known face encoding
        :param class_names: known face names
        :return:
        """
        box = self.mtcnn.detect(frame,True)
        # print(box)
        # print(box[0])
        # print('길이',len(box[0]))
        if box[0] is None:
            print('없')
        else:
            print('heeeeeeeeeeeeeeeeeeeeeeee')
            print(box)
            print(len(self.images),len(self.faces),len(self.class_names))
            for f, c in zip(self.faces,self.class_names):
                print('for loop')
                distance = self.compare2face(f, frame, box)
                print('여기까진?')
                threshold = 0.7  # set yourself to meet your requirement
                print("distance = " + str(distance),' 사진번호: ', c)
                name = 'unknonw'
                if (distance <= threshold):
                    name = c
                    print(name)
                    print("distance = " + str(distance), ' 인덱: ', c)
                self.mark_attendance(name)
        return frame

    def mark_attendance(self, name):
        """
        :param name: detected face known or unknown one
        :return:
        """

        if name != 'unknonw':
            print(name)
            self.logIn(name)


    def logIn(self, name):
        customer_id = int(name)
        DB = DB_Connection()
        cnt = DB.select_user(customer_id)

        if cnt[0] == "False":
            greeting = ' Welcome, ' + cnt[1] + '.'
            print(name, '님이 입장하셨습니다.')
            DB.update_login_session_T(customer_id)
            DB.insert_check_In_Time(customer_id)

            self.GreetingLabel.setText(greeting)
            self.timer1 = QTimer(self)
            self.timer1.start(5000)

            self.timer1.timeout.connect(self.clearLabel)

    def clearLabel(self):
        self.GreetingLabel.clear()

    def update_frame(self):
        path = '/home/ftpuser/ftp/files/'
        new_attendance_list = os.listdir(path)
        image_num = len(new_attendance_list)
        ret, image = self.capture.read()
        if image_num == self.attendance_num:
            self.displayImage(image)
        else:
            for cl in new_attendance_list:
                if os.path.splitext(cl)[0] not in self.class_names:
                    cur_img = cv2.imread(f'{path}/{cl}')
                    faces_detected = 0
                    start = time.time()
                    # result = self.detector.detect_faces(cur_img)
                    box = self.mtcnn.detect(cur_img, True)
                    faces_detected += len(box)
                    print(
                        f'Frames per second: {(time.time() - start):.3f},',
                        f'faces detected: {faces_detected}\r'
                    )
                    face = self.getFace(cur_img, box)
                    self.faces.append(face)
                    self.class_names.append(os.path.splitext(cl)[0])
            self.displayImage(image)


    def displayImage(self, image, window=1):
        """
        :param image: frame from camera
        :param encode_list: known face encoding list
        :param class_names: known face names
        :param window: number of window
        :return:
        """
        print(image.shape)
        try:
            image = self.face_rec_(image)
        except Exception as e:
            print('뭐지?',e)
        image = cv2.resize(image, (640, 480))
        qformat = QImage.Format_Indexed8
        if len(image.shape) == 3:
            if image.shape[2] == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888
        outImage = QImage(image, image.shape[1], image.shape[0], image.strides[0], qformat)
        outImage = outImage.rgbSwapped()

        if window == 1:
            self.imgLabel.setPixmap(QPixmap.fromImage(outImage))
            self.imgLabel.setScaledContents(True)

    def getFace(self, img, box):
        faces = []
        box = box[0][0]
        box = np.int32(box)
        # Result is an array with all the bounding boxes detected. We know that for 'ivan.jpg' there is only one.
        cv2.rectangle(img,
                      (box[0], box[1]), (box[2], box[3]),
                      (0, 155, 255),
                      2)
        cropped = img[box[1]:box[3],
                  box[0]:box[2]]
        rearranged = cv2.resize(cropped, (self.input_image_size, self.input_image_size), interpolation=cv2.INTER_CUBIC)
        prewhitened = pre_trained_facenet.prewhiten(rearranged)
        faces.append({'face': rearranged, 'embedding': self.getEmbedding(prewhitened)})
        return faces

    def getEmbedding(self, resized):
        reshaped = resized.reshape(-1, self.input_image_size, self.input_image_size, 3)
        feed_dict = {self.images_placeholder: reshaped, self.phase_train_placeholder: False}
        embedding = self.sess.run(self.embeddings, feed_dict=feed_dict)
        return embedding

    def compare2face(self, face, img2,  box2):
        face1 = face
        print('여기')
        face2 = self.getFace(img2,box2)
        print('여기2')
        if face1 and face2:
            dist = np.sqrt(np.sum(np.square(np.subtract(face1[0]['embedding'], face2[0]['embedding']))))
            return dist
        return -1

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = Check_In_Window()
    ui.show()
    sys.exit(app.exec_())
