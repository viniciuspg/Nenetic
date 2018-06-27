# -*- coding: utf-8 -*-
#
# Neural Network Image Classifier (Nenetic)
# Copyright (C) 2018 Peter Ersts
# ersts@amnh.org
#
# --------------------------------------------------------------------------
#
# This file is part of Neural Network Image Classifier (Nenetic).
#
# Andenet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Andenet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# --------------------------------------------------------------------------
import os
import json
import time
import numpy as np
from PyQt5 import QtWidgets, uic

from nenetic.workers import Extractor
from nenetic.workers import Trainer
from nenetic.workers import Classifier


CLASS_DIALOG, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'toolkit_widget.ui'))


class ToolkitWidget(QtWidgets.QDialog, CLASS_DIALOG):

    def __init__(self, canvas, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.canvas = canvas
        self.training_data = None
        self.directory = None

        self.extractor = None
        self.trainer = None
        self.classifier = None

        self.progress_max = 0
        self.pushButtonExtract.clicked.connect(self.extract_training_data)

        self.pushButtonTrainingData.clicked.connect(self.load_training_data)
        self.pushButtonTrainModel.clicked.connect(self.train_model)

        self.pushButtonLoadModel.clicked.connect(self.load_model)
        self.pushButtonClassify.clicked.connect(self.classify_image)
        self.pushButtonSaveClassification.clicked.connect(self.save_classification)

        self.checkBoxShowClassification.stateChanged.connect(self.show_classification)
        self.horizontalSliderOpacity.valueChanged.connect(self.canvas.set_opacity)

    def classify_image(self):
        if self.canvas.base_image is not None and self.classifier is not None:
            self.checkBoxShowClassification.setChecked(True)
            array = np.array(self.canvas.base_image)
            self.progressBar.setRange(0, array.shape[0])
            self.classifier.image = array
            self.classifier.threshold = self.doubleSpinBoxConfidence.value()
            self.pushButtonStopClassification.setEnabled(True)
            self.disable_action_buttons()
            self.classifier.start()

    def disable_action_buttons(self):
        self.pushButtonExtract.setEnabled(False)
        self.pushButtonTrainingData.setEnabled(False)
        self.pushButtonTrainModel.setEnabled(False)

        self.pushButtonClassify.setEnabled(False)
        self.pushButtonSaveClassification.setEnabled(False)
        self.pushButtonLoadModel.setEnabled(False)

    def enable_action_buttons(self):
        self.pushButtonExtract.setEnabled(True)
        self.pushButtonTrainingData.setEnabled(True)
        self.pushButtonTrainModel.setEnabled(True)

        self.pushButtonClassify.setEnabled(True)
        self.pushButtonSaveClassification.setEnabled(True)
        self.pushButtonLoadModel.setEnabled(True)

        self.pushButtonStopClassification.setEnabled(False)

    def extract_training_data(self):
        if self.directory is None:
            self.directory = self.canvas.directory
        file_name = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Training Data', os.path.join(self.directory, 'untitled.json'), 'Point Files (*.json)')
        if file_name[0] is not '':
            self.disable_action_buttons()
            self.directory = os.path.split(file_name[0])[0]

            package, point_count = self.canvas.package_points()
            self.progress_max = point_count
            self.progressBar.setRange(0, 0)

            tab = self.tabWidgetExtractors.currentIndex()
            extractor_name = self.tabWidgetExtractors.tabText(tab)
            kwargs = {}
            if extractor_name == 'Average':
                kwargs['kernels'] = self.spinBoxKernels.value()
                kwargs['solid_kernel'] = self.checkBoxSolidKernel.isChecked()
            elif extractor_name == 'Neighborhood':
                kwargs['pad'] = self.spinBoxNeighborhood.value() // 2

            self.extractor = Extractor(extractor_name, package, file_name[0], self.directory, kwargs)
            self.extractor.progress.connect(self.update_progress)
            self.extractor.feedback.connect(self.log)
            self.extractor.finished.connect(self.enable_action_buttons)
            self.extractor.start()

    def load_model(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Model', self.directory, 'Model Metadata (*.meta)')
        if file_name[0] is not '':
            self.classifier = Classifier(file_name[0])
            self.classifier.progress.connect(self.progressBar.setValue)
            self.classifier.feedback.connect(self.log)
            self.classifier.update.connect(self.canvas.update_classified_image)
            self.classifier.finished.connect(self.enable_action_buttons)

    def load_training_data(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Training Data', self.directory, 'Point Files (*.json)')
        if file_name[0] is not '':
            file = open(file_name[0], 'r')
            self.training_data = json.load(file)
            file.close()
            total_points = len(self.training_data['data'])
            vector_length = len(self.training_data['data'][0])
            num_classes = len(self.training_data['labels'][0])
            self.labelVectorLength.setText("{}".format(vector_length))
            self.labelNumberClasses.setText("{}".format(num_classes))
            self.labelTotalPoints.setText("{}".format(total_points))

    def log(self, tool, message):
        text = "[{}]({}) {}".format(time.strftime('%H:%M:%S'), tool, message)
        self.textBrowserConsole.append(text)

    def save_classification(self):
        if self.classifier is not None:
            file_name = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Classified Image', os.path.join(self.canvas.directory, 'untitled.jpg'), 'JPG (*.jpg)')
            if file_name[0] is not '':
                self.classifier.save_classification(file_name[0])

    def show_classification(self):
        self.canvas.toggle_classification(self.checkBoxShowClassification.isChecked())

    def train_model(self):
        if self.training_data is not None:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Save Model To Directory', self.directory)
            if directory != '':
                params = {}
                params['epochs'] = self.spinBoxEpochs.value()
                params['learning_rate'] = self.doubleSpinBoxLearningRate.value()
                params['l1_hidden_nodes'] = self.spinBoxL1.value()
                params['l2_hidden_nodes'] = self.spinBoxL2.value()
                params['validation_split'] = self.doubleSpinBoxSplit.value()
                self.trainer = Trainer(self.training_data, directory, params)

                self.progressBar.setRange(0, self.spinBoxEpochs.value())
                self.trainer.progress.connect(self.update_progress)
                self.trainer.feedback.connect(self.log)
                self.trainer.finished.connect(self.enable_action_buttons)
                self.disable_action_buttons()
                self.trainer.start()

    def update_progress(self, value):
        if self.progressBar.minimum() == self.progressBar.maximum():
            self.progressBar.setRange(0, self.progress_max)
        self.progressBar.setValue(value)