# This file is the main file for the GUI that transforms, stitches, and integrates detector data into 
# Q-chi plots, stitched plots, and one dimensional graphs with peak fitting capabilities. 
#
# This is one of the seven main files (IntegrateThread, MONster, monster_queueloader, monster_transform, monster_stitch, TransformThread, StitchThread) that controls the MONster GUI. 
#
# Runs with PyQt4, SIP 4.19.3, Python version 2.7.5
# 
# Author: Arun Shriram
# Written for my SLAC Internship at SSRL
# File Start Date: June 25, 2018
# File End Date: 
#
#
#
import numpy as np
import glob
import numpy
import Tkinter, tkFileDialog
from saveDimRedPack import save_Qchi, save_1Dplot, save_1Dcsv, save_texture_plot_csv
###############################################################
from peakBBA import peakFitBBA
from save_wafer_heatMap import FWHMmap, contrastMap
from input_file_parsing import parse_calib
import time
import monster_transform as mt
import monster_stitch as ms
import monster_integrate as mi
import monster_queueloader as mq
import Properties
#=====================
import sys
import os, traceback, ast
import getpass
import datetime
from ClickableLineEdit import *
from TransformThread import *
from IntegrateThread import *
from StitchThread import *
from PyQt4.QtGui import *
from PyQt4.QtCore import *

# This class defines the Detector window in the menu.
class DetectorEditor(QWidget):
    def __init__(self, windowreference):
        QWidget.__init__(self)
        self.windowreference = windowreference
        self.listwidget = QListWidget()
        self.listwidget.setMaximumWidth(350)
        self.listwidget.setMinimumWidth(250)
    
        detectors = Properties.detectors 
        self.detectorlist = []
        for item in detectors:
            string = item.split(', ')
            name = string[0]
            width = int(string[1][7:].rstrip())
            height = int(string[2][7:].rstrip())
            detector = Detector(name, width, height)
            self.detectorlist.append(detector)
            self.windowreference.detectorList.append(detector)
            self.listwidget.addItem(str(detector))
            self.windowreference.detector_combo.addItem(str(detector))
            
        

        self.removeButton = QPushButton("Remove")
        self.nameLabel = QLabel("Name")
        self.name = QLineEdit()
        self.widthLabel = QLabel("Width")
        self.width = QLineEdit()
        self.heightLabel = QLabel("Height")
        self.height = QLineEdit()
        self.addButton = QPushButton("Add to List!")
        self.closeButton = QPushButton("Close")

        hbox = QHBoxLayout()
        v1 = QVBoxLayout()
        v2 = QVBoxLayout()
        v2_h = QHBoxLayout()

        v1.addWidget(self.listwidget)
        v1.addWidget(self.removeButton)

        v2.addWidget(self.nameLabel)
        v2.addWidget(self.name)
        vx = QVBoxLayout()
        vy = QVBoxLayout()
        vx.addWidget(self.widthLabel)
        vx.addWidget(self.width)
        vy.addWidget(self.heightLabel)
        vy.addWidget(self.height)
        v2_h.addLayout(vx)
        v2_h.addLayout(vy)
        v2.addLayout(v2_h)
        v2.addWidget(self.addButton)
        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(self.closeButton)
        v2.addLayout(h)
        hbox.addLayout(v1)
        hbox.addLayout(v2)
        self.setLayout(hbox)
    
        self.setWindowTitle("Add or edit a detector!")
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())    



        self.updateConnections()        

     

    def updateConnections(self):
        self.closeButton.clicked.connect(lambda: self.close())
        self.addButton.clicked.connect(self.addDetector)
        self.name.returnPressed.connect(self.addDetector)
        self.width.returnPressed.connect(self.addDetector)
        self.height.returnPressed.connect(self.addDetector)

    def addDetector(self):
        if self.name.text().isEmpty() or self.width.text().isEmpty() or self.height.text().isEmpty():
            displayError(self, "Please make sure you fill out all the relevant information!")
            return
        try:
            name = str(self.name.text())
            width = int(str(self.width.text()))
            height = int(str(self.height.text()))
        except:
            displayError(self, "Could not add your values.")
            return
        detector = Detector(name, width, height)
        self.detectorlist.append(detector)
        properties = []
        inFile = open("Properties.py", 'r')
        for line in inFile:
            properties.append(line)
        inFile.close()
        outFile = open("Properties.py", 'w')
        detectors = properties[-1].split("= ")[1]
        detectors = ast.literal_eval(detectors)
        detectors.append(str(detector))
        properties[-1] = detectors
        for prop in properties:
            if prop == properties[-1]:
                s = "detectors = "
                prop = s + str(prop)
            outFile.write(str(prop))
        outFile.close()  
        self.listwidget.addItem(str(detector))
        self.windowreference.detector_combo.addItem(str(detector))
        
# This class is the class that governs all things that occur in the GUI window.
class MONster(QTabWidget):
    def __init__(self):
        QTabWidget.__init__(self)
        self.macroQueue = [] # list of macros for the queue tab
        self.fileProcessedCount = 0
        self.lineEditStyleSheet ="QLineEdit { border-radius: 4px;  color:rgb(0, 0, 0); background-color: rgb(255, 255, 255); border-style:outset; border-width:4px;  border-radius: 4px; border-color: rgb(34, 200, 157); color:rgb(0, 0, 0); background-color: rgb(200, 200, 200); } "
        self.textStyleSheet = "QLabel {background-color : rgb(29, 30, 50); color: white; }"
        self.current_user = getpass.getuser()
        screenShape = QDesktopWidget().screenGeometry()
        self.imageWidth = screenShape.height()/2.5
        mt.generateTransformWidgets(self) 
        ms.generateStitchWidgets(self)
        mi.generateIntegrateWidgets(self)
        mq.generateQueueWidgets(self)
        self.transformTab = QWidget()
        self.stitchTab = QWidget()
        self.integrateTab = QWidget()
        self.queueTab = QWidget()
        self.editor = mq.MacroEditor(self) # reference to the queue macro editor
        self.detectorWindow = DetectorEditor(self)
        self.processDone = True # To check if current process in the macro queue is over
        self.transformThread = TransformThread(self, None, None, None, None)  # initialize the transform thread
        self.integrateThread = IntegrateThread(self, None, None, None, None, None) # initialize the integrate thread
        self.stitchThread = StitchThread(self, None, None) # initialize the stitch thread        
        self.updateUi()
        
    # Generates layouts and sets connections between buttons and functions
    def updateUi(self):

        self.transformTab.setLayout(mt.generateTransformLayout(self))
        self.stitchTab.setLayout(ms.generateStitchLayout(self))
        self.integrateTab.setLayout(mi.generateIntegrateLayout(self))
        self.queueTab.setLayout(mq.generateQueueLayout(self))
        self.addTab(self.transformTab, "Transform")
        self.addTab(self.stitchTab, "Stitch")
        self.addTab(self.integrateTab, "Integrate")
        self.addTab(self.queueTab, "Queue Loader")
        self.show()
        self.raise_()
 
        
        ############################################
        ##############CONNECTIONS#################
        ############################################
        self.data_folder_button.clicked.connect(self.getDataSourceDirectoryPath)
        
        self.calib_folder_button.clicked.connect(self.getCalibSourcePath)
        
        self.processed_location_folder_button.clicked.connect(self.setProcessedLocation)
        
        self.start_button.clicked.connect(lambda: mt.transformThreadStart(self))
        
        self.q_min.returnPressed.connect(lambda: mt.transformThreadStart(self))
        
        self.q_min.clicked.connect(lambda: self.q_min.selectAll())        
        
        self.q_max.returnPressed.connect(lambda: mt.transformThreadStart(self))
        
        self.q_max.clicked.connect(lambda: self.q_max.selectAll())
        
        self.chi_min.returnPressed.connect(lambda: mt.transformThreadStart(self))
        
        self.chi_min.clicked.connect(lambda: self.chi_min.selectAll())
        
        self.chi_max.returnPressed.connect(lambda: mt.transformThreadStart(self))
        
        self.chi_max.clicked.connect(lambda: self.chi_max.selectAll())
        
        self.data_source.returnPressed.connect(lambda: mt.transformThreadStart(self))
                
        self.calib_source.returnPressed.connect(lambda: mt.transformThreadStart(self))
                
        self.saveCustomCalib.clicked.connect(self.saveCalibAction)
        
        self.abort.clicked.connect(self.transformThread.abortClicked)
        
        self.int_abort.clicked.connect(self.integrateThread.abortClicked)
        
        self.stitch_abort.clicked.connect(self.stitchThread.abortClicked)
        
        self.addMacroButton.clicked.connect(lambda: mq.addMacro(self))
        
        self.currentChanged.connect(self.windowTabChanged)
        
        self.addToQueueButton.clicked.connect(self.addCurrentToQueue)
        
        self.removeButton.clicked.connect(lambda: mq.removeMacro(self))
        
        self.int_start_button.clicked.connect(lambda: mi.integrateThreadStart(self))
        
        self.int_abort.clicked.connect(self.integrateThread.abortClicked)
        
        self.int_calib_folder_button.clicked.connect(lambda: mi.getIntCalibSourcePath(self))
        
        self.int_data_folder_button.clicked.connect(lambda: mi.getIntDataSourceDirectoryPath(self))
        
        self.int_processed_location_folder_button.clicked.connect(lambda: mi.setIntProcessedLocation(self))
        
        self.int_saveCustomCalib.clicked.connect(lambda: mi.saveIntCalibAction(self))
        
        self.startQueueButton.clicked.connect(lambda: mq.beginQueue(self))
        
        self.saveMacroButton.clicked.connect(lambda: mt.saveMacro(self))
        
        self.stitch_start_button.clicked.connect(lambda: ms.beginStitch(self))
        
        self.images_select_files_button.clicked.connect(lambda: ms.stitchImageSelect(self))
        
        self.stitch_saveLocation_button.clicked.connect(lambda: ms.setStitchSaveLocation(self))
        
        self.centerButton.clicked.connect(lambda: mi.centerButtonClicked(self))
      
        ###########################################
        ###########################
        #Restore default graphs and data from the previous run upon starting MONster
        ###########################
        # Properties.py has the following information from previous run(s), in this order:
        #
        #
        # Transform data source
        # Stitch data source
        # Integrate data source
        # Transform calibration source
        # Integrate calibration source
        # Transform processed location
        # Stitch processed location
        # Integrate processed location
        # Qchi image location
        # Stitched image location
        # Integrated image location
        # Q min
        # Q max
        # Chi min
        # Chi max
        # First index for stitch scan
        # Last index for stitch scan
        
        try:
            if os.path.exists(Properties.t_data_source):
                dataPath = Properties.t_data_source
                self.data_source.setText(dataPath)
                self.files_to_process = [dataPath]                
            if os.path.exists(Properties.s_data_source):
                self.images_select.setText(Properties.s_data_source)                
            if os.path.exists(Properties.i_data_source):
                self.int_data_source.setText(Properties.i_data_source)
            if os.path.exists(Properties.t_calib_source):
                self.calib_source.setText(Properties.t_calib_source)
            if os.path.exists(Properties.i_calib_source):
                self.int_calib_source.setText(Properties.i_calib_source)
            if os.path.exists(Properties.t_processed_loc):
                self.processed_location.setText(Properties.t_processed_loc)
            else:
                self.processed_location.setText(str(self.data_source.text()) + "/Processed_Transform")
            if os.path.exists(Properties.s_processed_loc):
                self.stitch_saveLocation.setText(Properties.s_processed_loc)
            else:
                self.stitch_saveLocation.setText(str(self.images_select.text())  + "/Processed_Stitch")                
            if os.path.exists(Properties.i_processed_loc):
                self.int_processed_location.setText(Properties.i_processed_loc)
            else:
                self.int_processed_location.setText(str(self.int_data_source.text()) + "/Processed_Integrate")                
                
            self.setRawImage(Properties.two_d_image)
            ms.setStitchImage(self, Properties.stitch_image)
            mi.set1DImage(self, Properties.one_d_image)
            self.q_min.setText(Properties.qmin)
            self.q_max.setText(Properties.qmax)
            self.chi_min.setText(Properties.chimin)
            self.chi_max.setText(Properties.chimax)

        except:
            traceback.print_exc()
            self.addToConsole("Something's not right with the previous run information.")
            self.setRawImage('images/SLAC_LogoSD.png')
            mi.set1DImage(self, 'images/SLAC_LogoSD.png')       
            if str(self.processed_location.text()) == "":
                self.processed_location.setText(str(self.data_source.text()) + "/Processed_Transform")
            if str(self.int_processed_location.text()) == "":
                self.int_processed_location.setText(str(self.int_data_source.text()) + "/Processed_Integrate")
            if str(self.stitch_saveLocation.text()) == "":
                self.stitch_saveLocation.setText(str(self.images_select.text())  + "/Processed_Stitch")
        
        self.loadCalibration()
        self.loadIntegrateCalibration()
        
        self.setStyleSheet("background-color: rgb(29, 30,51);")
   
    # Compiles the information on the current transform tab page into a macro and adds it to the queue
    def addCurrentToQueue(self):
        cur_time = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        name = ('/Users/arunshriram/Documents/SLAC Internship/monhitp-gui/macros/transform-macro-%s') %(cur_time)
        self.addToConsole("Saving this page in directory \"macros\" as \"transform-macro-%s\" and adding to the queue..." % (cur_time))
        mt.saveMacro(self, name)
        mq.addMacroToQueue(self)
        self.addToConsole("Macro saved and added to queue!")
        
    # Copies all the information from the transform tab to either the macro editor or the integrate tab.
    def windowTabChanged(self, index):
        if index == 3:
            self.editor.q_min.setText(self.q_min.text())
            self.editor.q_max.setText(self.q_max.text())
            self.editor.chi_min.setText(self.chi_min.text())
            self.editor.chi_max.setText(self.chi_max.text())
            self.editor.detectordistance.setText(self.detectordistance.text())
            self.editor.detect_tilt_alpha.setText(self.detect_tilt_alpha.text())
            self.editor.detect_tilt_delta.setText(self.detect_tilt_delta.text())
            self.editor.dcenterx.setText(self.dcenterx.text())
            self.editor.dcentery.setText(self.dcentery.text())
            self.editor.wavelength.setText(self.wavelength.text())
            self.editor.calib_source.setText(self.calib_source.text())
            self.editor.processed_location.setText(self.processed_location.text())
            self.editor.data_source.setText(self.data_source.text())       
            self.editor.int_detectordistance.setText(self.int_detectordistance.text())
            self.editor.int_detect_tilt_alpha.setText(self.int_detect_tilt_alpha.text())
            self.editor.int_detect_tilt_delta.setText(self.int_detect_tilt_delta.text())
            self.editor.int_dcenterx.setText(self.int_dcenterx.text())
            self.editor.int_dcentery.setText(self.int_dcentery.text())
            self.editor.int_wavelength.setText(self.int_wavelength.text())
            self.editor.int_calib_source.setText(self.int_calib_source.text())
            self.editor.int_processed_location.setText(self.int_processed_location.text())
            self.editor.int_data_source.setText(self.int_data_source.text())                   
            
            if self.data_source_check.isChecked():
                self.editor.data_source_check.setChecked(True)
            else:
                self.editor.data_source_check.setChecked(False)
        #elif index == 2:
            #self.int_detectordistance.setText(self.detectordistance.text())
            #self.int_detect_tilt_alpha.setText(self.detect_tilt_alpha.text())
            #self.int_detect_tilt_delta.setText(self.detect_tilt_delta.text())
            #self.int_dcenterx.setText(self.dcenterx.text())
            #self.int_dcentery.setText(self.dcentery.text())
            #self.int_wavelength.setText(self.wavelength.text())
            #self.int_calib_source.setText(self.calib_source.text())
            #self.int_processed_location.setText(self.processed_location.text())
            #self.int_data_source.setText(self.data_source.text())            
            #if self.data_source_check.isChecked():
                #self.int_data_source_check.setChecked(True)
            #else:
                #self.int_data_source_check.setChecked(False)            
        
    # disables all widgets except abort
    def disableWidgets(self):
        for editor in self.findChildren(ClickableLineEdit):
            editor.setDisabled(True)
        for button in self.findChildren(QPushButton):
            if button != self.abort and button != self.int_abort and button != self.stitch_abort:
                button.setDisabled(True)
        for box in self.findChildren(QCheckBox):
            box.setDisabled(True)
        self.detector_combo.setDisabled(True)

    # enables all widgets
    def enableWidgets(self):
        for editor in self.findChildren(ClickableLineEdit):
            editor.setEnabled(True)
        for button in self.findChildren(QPushButton):
                button.setEnabled(True)
        for box in self.findChildren(QCheckBox):
            box.setEnabled(True)
        self.detector_combo.setEnabled(True)

   
        
    
    # What should be done after a stitch thread is finished
    def stitchDone(self, loopTime):
        avgTime = np.mean(loopTime)
        maxTime = np.max(loopTime)
        finishedMessage = ''
        finishedMessage += ('====================================================\n')
        finishedMessage += ('====================================================\n')
        finishedMessage += ('Files finished processing\n')
        finishedMessage += ('-----Avg {:.4f}s / file, max {:.4f}.s / file\n'.format(avgTime, maxTime))
        finishedMessage += ('-----Total Time Elapsed {:4f}s\n'.format(np.sum(loopTime)))
        finishedMessage += ('====================================================\n')
        finishedMessage += ('====================================================')    
        self.console.moveCursor(QTextCursor.End)
        self.miconsole.moveCursor(QTextCursor.End)
        self.qconsole.moveCursor(QTextCursor.End)
        self.stitch_console.moveCursor(QTextCursor.End)
        #QMessageBox.information(self, "Done!", finishedMessage)
        self.addToConsole(finishedMessage)
        QApplication.processEvents()            
        self.enableWidgets()
        self.stitchThread.quit()
        self.stitchThread.stop()
        self.processDone = True
    
    # What should be done after a thread is finished
    def done(self, loopTime, stage1Time, stage2Time):
        avgTime = np.mean(loopTime)
        maxTime = np.max(loopTime)
        avg1 = np.mean(stage1Time)
        avg2 = np.mean(stage2Time)
        max1 = np.max(stage1Time)
        max2 = np.max(stage2Time)
        finishedMessage = ''
        finishedMessage += ('====================================================\n')
        finishedMessage += ('====================================================\n')
        finishedMessage += ('Files finished processing\n')
        finishedMessage += ('-----Avg {:.4f}s / file, max {:.4f}.s / file\n'.format(avgTime, maxTime))
        finishedMessage += ('-----Stage1: Avg {:.4f}s / file, max {:.4f}.s / file\n'.format(avg1, max1))
        finishedMessage += ('-----Stage2: Avg {:.4f}s / file, max {:.4f}.s / file\n'.format(avg2, max2))
        finishedMessage += ('-----Total Time Elapsed {:4f}s\n'.format(np.sum(loopTime)))
        finishedMessage += ('====================================================\n')
        finishedMessage += ('====================================================')        
        #QMessageBox.information(self, "Done!", finishedMessage)
        self.addToConsole(finishedMessage)
        self.console.moveCursor(QTextCursor.End)
        self.miconsole.moveCursor(QTextCursor.End)
        self.qconsole.moveCursor(QTextCursor.End)
        self.stitch_console.moveCursor(QTextCursor.End)        
        QApplication.processEvents()            
        self.enableWidgets()
        self.transformThread.quit()
        self.integrateThread.quit()
        self.stitchThread.quit()
        #self.transformThread.deleteLater()
        #if self.transformThread.isRunning():
        #self.transformThread.quit()
        self.stitchThread.stop()
        self.transformThread.stop() 
        self.integrateThread.stop() 
        self.processDone = True
        
    # Adds the passed in message to all consoles
    def addToConsole(self, message):
        self.console.append(message)
        self.miconsole.append(message)
        self.qconsole.append(message)
        self.stitch_console.append(message)
        self.console.moveCursor(QTextCursor.End)
        self.miconsole.moveCursor(QTextCursor.End)
        self.qconsole.moveCursor(QTextCursor.End)
        self.stitch_console.moveCursor(QTextCursor.End)
        QApplication.processEvents()
   
    # Loads transform calibration information based on the filename the user selects
    def loadCalibration(self):
        if str(self.calib_source.text()) != '':
            try:
                d_in_pixel, Rotation_angle, tilt_angle, lamda, x0, y0 = parse_calib(str(self.calib_source.text()))
            except:
                self.addToConsole("Unable to locate calibration source file.")
                return
            self.wavelength.setText(str(lamda))
            self.detectordistance.setText(str(d_in_pixel))
            self.dcenterx.setText(str(x0))
            self.dcentery.setText(str(y0))
            self.detect_tilt_alpha.setText(str(Rotation_angle))
            self.detect_tilt_delta.setText(str(tilt_angle))
     
     # Loads integrate calibration information based on the filename the user selects          
    def loadIntegrateCalibration(self):
        if str(self.int_calib_source.text()) != '':
            try:
                d_in_pixel, Rotation_angle, tilt_angle, lamda, x0, y0 = parse_calib(str(self.int_calib_source.text()))
            except:
                self.addToConsole("Unable to locate calibration source file.")
                return
            self.int_wavelength.setText(str(lamda))
            self.int_detectordistance.setText(str(d_in_pixel))
            self.int_dcenterx.setText(str(x0))
            self.int_dcentery.setText(str(y0))
            self.int_detect_tilt_alpha.setText(str(Rotation_angle))
            self.int_detect_tilt_delta.setText(str(tilt_angle))
                                      
    # Loads the appropriate files based on the data source the user selects
    def getDataSourceDirectoryPath(self):
        if self.data_source_check.isChecked():
            try:
                folderpath = str(QFileDialog.getExistingDirectory())
                if folderpath != '':
                    self.data_source.setText(folderpath)
                    self.data_label.setText("Current data source:")
                    self.processed_location.setText(str(self.data_source.text())  + "/Processed_Transform")
                    self.files_to_process = [folderpath]
            except:
                self.addToConsole("Something went wrong when trying to open your directory.")
        else:
            try:
                
                filenames = QFileDialog.getOpenFileNames(self, "Select the files you wish to use.")
                filenames = [str(filename) for  filename in filenames]
                if len(filenames) < 2:
                    self.data_label.setText("Current data source: %s" % os.path.basename(filenames[0]))
                else:
                    self.data_label.setText("Current data source: (multiple files)")
                print(filenames)
                self.data_source.setText(os.path.dirname(filenames[0]))
                self.processed_location.setText(str(self.data_source.text())  + "/Processed_Transform")
                self.files_to_process = filenames
            except:
                #traceback.print_exc()
                self.addToConsole("Did not select a data source.")
    # Retrieves and loads the calibration information that the user selects
    def getCalibSourcePath(self):
        path = str(QFileDialog.getOpenFileName(self, "Select Calibration File", ('/Users/arunshriram/Documents/SLAC Internship/monhitp-gui/calib/')))
        if path !='':
            self.calib_source.setText(path)
            self.loadCalibration()
        
    # Saves the custom calibration that the user enters as a new calibration file
    def saveCalibAction(self):
        name = ('/Users/arunshriram/Documents/SLAC Internship/monhitp-gui/calib/cal-%s.calib') %(datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S'))
        fileName = QFileDialog.getSaveFileName(self, 'Save your new custom calibration!', name)
        try:
            with open(fileName, 'w') as calib:
                for i in range(6):
                    calib.write('-\n')
                calib.write("bcenter_x=" + str(self.dcenterx.text()) + '\n')
                calib.write("bcenter_y=" + str(self.dcentery.text()) + '\n')
                calib.write("detect_dist=" + str(self.detectordistance.text()) + '\n')
                calib.write("detect_tilt_alpha=" + str(self.detect_tilt_alpha.text()) + '\n')
                calib.write("detect_tilt_delta=" + str(self.detect_tilt_delta.text()) + '\n')
                calib.write("wavelength=" + str(self.wavelength.text()) + '\n')
                calib.write('-\n')
            self.calib_source.setText(os.path.expanduser(str(fileName)))
        except:
            self.addToConsole("Calibration could not be saved!")
            return

        
    # Argument is the filename of the q-chi plot, this displays the plot on the screen
    def setRawImage(self, filename):
        try:
            pixmap = QPixmap(filename)
            if filename == "":
                pixmap = QPixmap("images/SLAC_LogoSD.png")
            self.raw_image.setPixmap(pixmap.scaled(self.imageWidth, self.imageWidth, Qt.KeepAspectRatio))        
        except:
            self.addToConsole("Could not load Qchi image.")
            return
    # Asks the user for the location where the processed files should go          
    def setProcessedLocation(self):
        path = str(QFileDialog.getExistingDirectory(self, "Select a location for processed files", str(self.data_source.text())))
        #path = str(QFileDialog.getOpenFileName(self, "Select Calibration File", ('/Users/arunshriram/Documents/SLAC Internship/monhitp-gui/calib/')))
        if path !='':
            self.processed_location.setText(path)
        
    # Returns the number of lines in a file
    def file_len(self, fname):
        with open(fname) as f:
            for i, l in enumerate(f):
                pass
        return i + 1        
    

            
        
    
            

           
    # Sets the bar progress to whatever value is passed in
    def setRadialBar(self, bartype, val):
        if bartype == 1:
            self.int_bar.setValue(val)
        elif bartype == 0:
            self.bar.setValue(val)
        elif bartype == 2:
            self.stitchbar.setValue(val)
            
        self.queue_bar_files.setValue(val)
    # tuple -> None
    # Accepts the event of the mouse movement and updates the moving coordinate label accordingly (for 1D plots)
    def mouseMoved(self, evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        global  currentChannel
        if self.one_d_graph.sceneBoundingRect().contains(pos):
            mousePoint = self.vb.mapSceneToView(pos)
            yPoint = "{:.4e}".format(mousePoint.y())
            #self.graphcoordinates.setText("<span style='font-size: 11pt'>%s = %0.4f, <span style='color: red'>%s = %s</span>" % (str(self.currentMotor), mousePoint.x(), str(currentChannel), yPoint))
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())  
            #global coordinates 
            #coordinates = (round(mousePoint.x(), 4), round(mousePoint.y(), 4))   
        
    # None -> None
    # Updates the current 1D graph region        
    def updateRegion(self, window, viewRange):
        rgn = viewRange[0]
        self.region.setRegion(rgn)    
    
    # None -> None
    # Updates the current 1D graph ranges
    def update(self):
        self.region.setZValue(10)
        minX, maxX = self.region.getRegion()
        self.one_d_graph.setXRange(minX, maxX, padding=0)   
    
# Takes a message as an argument and displays it to the screen as a message box     
def displayError(self, message):
    message = QLabel(message)
    self.win = QWidget()
    self.win.setWindowTitle('Error')
    self.ok = QPushButton('Ok')
    self.ly = QVBoxLayout()
    self.ly.addWidget(message)
    self.ly.addWidget(self.ok)
    self.win.setLayout(self.ly)    
    self.ok.clicked.connect(lambda: self.win.close())
    self.win.show()
    self.win.raise_()
    


# Defines which lines are wanted/unwanted when writing previous run information during stitching
def stitch_is_wanted(line):
    if "s_data_source" in line or "findex" in line or "s_processed_loc" in line or "lindex" in line or "stitch_image" in line:
        return True
    return False    

# Defines which lines are wanted/unwanted when writing previous run information during integrating
def integrate_is_wanted(line):
    if "i_data_source" in line or "i_calib_source" in line or "qmin" in line or "qmax" in line or "chimin" in line or "chimax" in line or "i_processed_loc" in line or "one_d_image" in line:
        return True
    return False     

# This class is the governing class, the highest in the hiearchy. Its central widget is the main GUI window. 
class Menu(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        
        self.form_widget = MONster()
        self.setCentralWidget(self.form_widget)
        
        
        self.updateUi()
        
    def updateUi(self):
        bar = self.menuBar()
        file = bar.addMenu('File')
        edit = bar.addMenu("Edit")
        home_action = QAction('Home', self)
        
        save_action = QAction('Save', self)
        save_action.setShortcut('Ctrl+S')
        #saveplot_action = QAction('Save Plot Data', self)
        #saveplot_action.setShortcut('Ctrl+Alt+S')
        clear_prop = QAction("Clear previous run information", self)
        
        quit_action = QAction('Quit', self)
        quit_action.setShortcut('Ctrl+Q')

        detectors = QAction("Add or remove detectors", self)
        
        
        file.addAction(home_action)
        file.addAction(save_action)
        edit.addAction(clear_prop)
        edit.addAction(detectors)
        #file.addAction(saveplot_action)
        file.addAction(quit_action)
        
        
        quit_action.triggered.connect(lambda: qApp.quit())
        clear_prop.triggered.connect(self.clearProperties)
        detectors.triggered.connect(lambda: self.form_widget.detectorWindow.show())
        self.setWindowTitle('MONster')
        
        self.setStyleSheet("background-color: rgb(29, 30,51);")
        
        self.show()
        self.raise_()
        self.setFixedSize(self.minimumSizeHint())
        
    def clearProperties(self):
        detectors = []
        with open("Properties.py", 'r') as prop:
            for i in range(14):
                prop.readline()
            detectors = ast.literal_eval(prop.readline().split("= ")[1])
        with open("Properties.py", 'w') as prop:
            prop.write("t_data_source = \"\"\n")
            prop.write("s_data_source = \"\"\n")
            prop.write("i_data_source = \"\"\n")
            prop.write("t_calib_source = \"\"\n")
            prop.write("i_calib_source = \"\"\n")
            prop.write("t_processed_loc = \"\"\n")
            prop.write("s_processed_loc = \"\"\n")
            prop.write("i_processed_loc = \"\"\n")
            prop.write("two_d_image = \"\"\n")
            prop.write("stitch_image = \"\"\n")
            prop.write("one_d_image = \"\"\n")
            prop.write("qmin = \"\"\n")
            prop.write("qmax = \"\"\n")
            prop.write("chimin = \"\"\n")
            prop.write("chimax = \"\"\n")
            prop.write("detectors = " + str(detectors))
  
        
        
def main():
    app = QApplication(sys.argv)
    menu = Menu()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()