# -*- coding: utf-8 -*-
import sys
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPalette, QColor, QPixmap, QBitmap, QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QGraphicsPixmapItem, QGraphicsScene, QFileDialog

from reg_tool_ui import Ui_Form
from qt_material import apply_stylesheet

import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'
import glob
import shutil

import numpy as np
import cv2
import time


class MyMainForm(QMainWindow, Ui_Form):
    def __init__(self, parent=None):
        super(MyMainForm, self).__init__(parent)
        self.setupUi(self)
        
        extra = {'font_family': 'Times New Roman', 'font_size': 20}
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        path_css = os.path.abspath(os.path.join(bundle_dir, 'custom.css'))
        apply_stylesheet(app, 'light_blue.xml', invert_secondary=True, extra=extra, css_file=path_css)
        
        path_ico = os.path.abspath(os.path.join(bundle_dir, 'tools.ico'))
        self.setWindowIcon(QIcon(path_ico))
        
        self.pushButton.clicked.connect(self.control_up)
        self.pushButton_2.clicked.connect(self.control_down)
        self.pushButton_3.clicked.connect(self.control_left)
        self.pushButton_4.clicked.connect(self.control_right)
        self.pushButton_5.clicked.connect(self.control_prev)
        self.pushButton_6.clicked.connect(self.control_next)
        self.pushButton_7.clicked.connect(self.control_save)
        self.pushButton_8.clicked.connect(self.control_exit)
        self.pushButton_9.clicked.connect(self.control_open)

        self.horizontalSlider.setMaximum(100)      
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setSingleStep(5)
        self.horizontalSlider.setValue(30)
        self.horizontalSlider.valueChanged.connect(self.control_alpha)
        
        self.reg_image_path = './images/'
        if not os.path.exists(self.reg_image_path):
            os.makedirs(self.reg_image_path)
        self.reg_ir_path = self.reg_image_path + '/IR/'
        if not os.path.exists(self.reg_ir_path):
            os.makedirs(self.reg_ir_path)
        self.reg_vi_path = self.reg_image_path + '/VI/'
        if not os.path.exists(self.reg_vi_path):
            os.makedirs(self.reg_vi_path)
        
        self.alpha = 30
        self.index = -1
        self.save_index = 0
        
        # x是水平方向，y是竖直方向
        self.delta_x = 0
        self.delta_y = 0
        
        # self.show_next_image(1)
    
    def write_to_textbrowser(self, line):
        self.textBrowser.append(line)
        self.textBrowser.ensureCursorVisible()
    
    def draw_fused_image(self):
        y_begin = self.center_y - int(self.H * self.scale) - 60 + self.delta_y
        y_end = self.center_y + int(self.H * self.scale) + 60 + self.delta_y
        x_begin = self.center_x - int(self.W * self.scale) - 80 + self.delta_x
        x_end = self.center_x + int(self.W * self.scale) + 80 + self.delta_x
        self.vi_image_region = self.vi_image[y_begin : y_end, x_begin : x_end] # 修改这个变量
        
        fused_image = self.vi_image_region.copy()
        fused_image[60 : 60 + int(self.H * self.scale) * 2, 80 : 80 + int(self.W * self.scale) * 2] = \
            cv2.addWeighted(fused_image[60 : 60 + int(self.H * self.scale) * 2, 80 : 80 + int(self.W * self.scale) * 2], 
                            self.alpha/100, self.ir_image_resized, 1-self.alpha/100, 0.0)
        
        W_show = int(self.W * self.scale) * 2 + 80 * 2 # 904
        H_show = int(self.H * self.scale) * 2 + 60 * 2 # 678
        frame = QtGui.QImage(fused_image.copy().data, W_show, H_show, QtGui.QImage.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(frame)
        self.item = QGraphicsPixmapItem(pix)
        self.scene = QGraphicsScene()
        self.scene.addItem(self.item)
        self.graphicsView.setScene(self.scene)
        
    def show_next_image(self, foward=1):
        self.index = self.index + foward
        self.delta_x = 0
        self.delta_y = 0
        self.label.setText("filename: " + self.source_image_path + "my_irstream-" + str(self.index) + ".jpg")
        B = 23.5
        f = 17
        Z = 5000
        p = 12

        offset = (B * f / Z * 1000) / p * 2
        mismatch = 1 + int(Z / 1000)
        
        self.H = 480
        self.W = 640
        self.scale = 0.582

        matrix = np.float32([[self.scale, 0, (1 - self.scale) * self.W / 2 - mismatch], 
                             [0, self.scale, (1 - self.scale) * self.H / 2 - offset]])
        # print(matrix)
        center = np.float32([[self.W/2],[self.H/2],[1]])
        center_transformed = np.matmul(matrix, center)
        # print(center_transformed)

        self.center_x = center_transformed[0] * 2
        self.center_x = int(self.center_x.astype(int))
        self.center_y = center_transformed[1] * 2
        self.center_y = int(self.center_y.astype(int))

        self.ir_path = self.source_image_path + "/my_irstream-" + str(self.index) + ".jpg"
        self.vi_path = self.source_image_path + "/my_vistream-" + str(self.index) + ".png"
        
        self.ir_image = cv2.imread(self.ir_path, cv2.IMREAD_GRAYSCALE)
        self.ir_image = cv2.cvtColor(self.ir_image, cv2.COLOR_GRAY2RGB)

        self.vi_image = cv2.imread(self.vi_path)
        self.vi_image = cv2.cvtColor(self.vi_image, cv2.COLOR_BGR2RGB)

        self.ir_image_resized = cv2.resize(self.ir_image, (int(self.W * self.scale) * 2, int(self.H * self.scale) * 2), 
                                  interpolation=cv2.INTER_CUBIC)
        
        self.draw_fused_image()
        
    def control_open(self):
        self.source_image_path = 'E:/FLIR A700/python/spinnaker_python/Examples/my_demo/images/'
        self.source_image_path = QFileDialog.getExistingDirectory(self, "select a folder", "./")
        self.source_image_path = self.source_image_path + '/'
        
        self.file_count = len(glob.glob(self.source_image_path + "*.jpg"))
        if self.file_count == 0:
            print("source images not found")
            self.write_to_textbrowser("source images not found")
            return
        
        self.write_to_textbrowser("find " + str(self.file_count) + " pairs of images")
        
        self.index = -1
        self.show_next_image(1)
    
    def control_up(self):
        self.delta_y = self.delta_y + 1
        self.draw_fused_image()
    
    def control_down(self):
        self.delta_y = self.delta_y - 1
        self.draw_fused_image()
    
    def control_left(self):
        self.delta_x = self.delta_x - 1
        self.draw_fused_image()
    
    def control_right(self):
        self.delta_x = self.delta_x + 1
        self.draw_fused_image()
    
    def control_prev(self):
        if self.index > 0:
            self.show_next_image(-1)
    
    def control_next(self):
        if self.index < self.file_count-1:
            self.show_next_image(1)
    
    def control_save(self):
        y_begin = self.center_y - int(self.H * self.scale) + self.delta_y
        y_end = self.center_y + int(self.H * self.scale) + self.delta_y
        x_begin = self.center_x - int(self.W * self.scale) + self.delta_x
        x_end = self.center_x + int(self.W * self.scale) + self.delta_x
        
        self.cropped_vi_image = self.vi_image[y_begin : y_end, x_begin : x_end]
        self.cropped_vi_image = cv2.resize(self.cropped_vi_image,(640, 480),interpolation=cv2.INTER_CUBIC)
        self.cropped_vi_image = cv2.cvtColor(self.cropped_vi_image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(self.reg_vi_path + "/vi-" + str(self.save_index) + ".png", self.cropped_vi_image)
        shutil.copy(self.ir_path, self.reg_ir_path + "/ir-" + str(self.save_index) + ".jpg")
        self.write_to_textbrowser("registered images saved, index = " + str(self.save_index))
        self.save_index = self.save_index + 1
    
    def control_alpha(self):
        self.alpha = self.horizontalSlider.value()
        fused_image = self.vi_image_region.copy()
        fused_image[60 : 60 + int(self.H * self.scale) * 2, 80 : 80 + int(self.W * self.scale) * 2] = \
            cv2.addWeighted(fused_image[60 : 60 + int(self.H * self.scale) * 2, 80 : 80 + int(self.W * self.scale) * 2], 
                            self.alpha/100, self.ir_image_resized, 1-self.alpha/100, 0.0)
        
        W_show = int(self.W * self.scale) * 2 + 80 * 2 # 904
        H_show = int(self.H * self.scale) * 2 + 60 * 2 # 678
        frame = QtGui.QImage(fused_image.copy().data, W_show, H_show, QtGui.QImage.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(frame)
        self.item = QGraphicsPixmapItem(pix)
        self.scene = QGraphicsScene()
        self.scene.addItem(self.item)
        self.graphicsView.setScene(self.scene)
        
    def control_exit(self):
        app.quit()
        self.close()
    
    def closeEvent(self, event):
        app.quit()
        self.close()
        
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWin = MyMainForm()
    myWin.show()
    sys.exit(app.exec_())