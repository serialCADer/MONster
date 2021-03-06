# This file initializes the various widgets used in the queue loader tab and its layout. It also
# includes a class that defines what a Macro is and a class for the macro editor itself, interfacing that
# with MONster.
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os, traceback, glob
from ClickableLineEdit import *
import datetime
from input_file_parsing import parse_calib
from MONster import displayError
from IntegrateThread import *
from TransformThread import *
from StitchThread import *
import monster_stitch as ms
import monster_integrate as mi
from QRoundProgressBar import QRoundProgressBar
from TransformThread import Detector
import csv, ast
curIndex = 1

class Macro():
    def __init__(self, filename, dictionary):
        self.filename = filename
        self.mdict = dictionary
        
    def isWorkflow(self):
        return self.mdict['workflow']

    def getFilename(self):
        return self.filename
    
    def setCalibInfo(self, calib_source):
        self.mdict['t_calib_source'] = calib_source
        self.parseDetectorData()

    def getTDataFiles(self):
        return self.mdict['t_data_source']
    
    def getSDataFiles(self):
        return self.mdict['s_data_source']
        
    def getIDataFiles(self):
        return self.mdict['i_data_source']
        
    def shouldTransform(self):
        return self.mdict['transform']
    
    def shouldStitch(self):
        return self.mdict['stitch']
    
    def shouldIntegrate(self):
        return self.mdict['integrate']
    
    def getQRange(self):
        return (self.mdict['qmin'], self.mdict['qmax'])
    
    def getTProcessedFileDir(self):
        return self.mdict['t_proc_dir']
    
    def getIProcessedFileDir(self):
        return self.mdict['i_proc_dir']
    
    def getSProcessedFileDir(self):
        return self.mdict['s_proc_dir']
    
    def getTCalibInfo(self):
        return self.mdict['t_calib_source']
    
    def getICalibInfo(self):
        return self.mdict['i_calib_source']    
    
    def getChiRange(self):
        return (self.mdict['chimin'], self.mdict['chimax'])
    
    def parseDetectorData(self):
        try:
            d_in_pixel, Rotation_angle, tilt_angle, lamda, x0, y0 = parse_calib(self.mdict['t_calib_source'])
        except:
            traceback.print_exc()
            return
        if self.shouldTransform():
            return (d_in_pixel, Rotation_angle, tilt_angle, lamda, x0, y0, self.mdict['detector_type'])
        else:
            return (d_in_pixel, Rotation_angle, tilt_angle, lamda, x0, y0)
            
    def getDetectorData(self):
        return self.parseDetectorData()
    
class MacroEditor(QWidget):
    def __init__(self, windowreference):
        QWidget.__init__(self)
    
        self.fieldsChanged = False
        self.curMacro = None        
        self.t_files_to_process = []        
        self.s_files_to_process = []
        self.i_files_to_process = []
        self.detectorList = []
        
        self.windowreference = windowreference
        # Stack information (Qstack, that is)
        self.Stack = QStackedWidget(self)
        self.welcome = QWidget()
        self.transformStack = QWidget()
        self.stitchStack = QWidget()
        self.integrateStack = QWidget()
        self.Stack.addWidget(self.welcome)
        self.Stack.addWidget(self.transformStack)
        self.Stack.addWidget(self.stitchStack)
        self.Stack.addWidget(self.integrateStack)
        self.stackList = QListWidget()
        self.stackList.insertItem(0, "Macro Editor")
        self.stackList.insertItem(1, "Transform")
        self.stackList.insertItem(2, "Stitch")
        self.stackList.insertItem(3, "Integrate")
        self.stackList.setFont(QFont("Georgia", 20))
        self.stackList.setFixedWidth(200)
        self.stackList.setSpacing(20)
     
        self.saveButton = QPushButton("Save this macro")
        self.saveButton.setMaximumWidth(180)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setMaximumWidth(180)
        self.addToQueueButton = QPushButton("Add this macro the queue!")
        self.addToQueueButton.setMaximumWidth(180)
        self.loadMacroButton = QPushButton("Load a macro")
        self.loadMacroButton.setMaximumWidth(180)
        

        hbox = QHBoxLayout()
        hbox.addWidget(self.stackList)
        hbox.addWidget(self.Stack)
        v = QVBoxLayout()
        v.addWidget(self.saveButton)
        v.addWidget(self.loadMacroButton)
        v.addWidget(self.addToQueueButton)
        v.addWidget(self.cancelButton)
        hbox.addLayout(v)
        self.setLayout(hbox)
        
        self.stack1UI()
        self.stack2UI()
        self.stack3UI()        
        self.stack0UI() # needs to be done last because the other widgets need to be initialized before we can disable or enable them
        
        
    
        self.setWindowTitle("Add or edit a macro!")
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())        
        self.updateConnections()        
        
    def display(self, i):
        self.Stack.setCurrentIndex(i)        
        
    def stack0UI(self):

        self.tipLabel = QLabel("Note: Always save any changes you make before adding to the queue! Unsaved changes will not update the macro.")
        message = "The Macro Editor is a tool to help make large processes a little faster to put together and easier to automate. \nNow, you can Transform, Stitch, or Integrate your files easily! Simply check which of the processes you want \nto be performed, edit the appropriate settings within each field, save your macro, and add it to the \nqueue! You can also load previously saved macros and add them to the queue or edit them."
        self.infoLabel = QLabel(message)
        
        self.macroSelected = QLabel("Current macro selected: ")
    

        font = QFont()
        font.setBold(True)
        self.macroSelected.setFont(font)


        self.checkLabel = QLabel("Select at one of the following:")
        self.workflowCheckLabel = QLabel("Select a data source and set the appropriate calibration, \nprocessed location, and Q and Chi range parameters. The transform \nprocesss will output .mat files, which will be stitched together \nand then integrated.")

        def workflowClicked():
            self.transformCheck.setDisabled(True)
            self.stitchCheck.setDisabled(True)
            self.integrateCheck.setDisabled(True)
            self.images_select.setDisabled(True)
            self.images_select_files_button.setDisabled(True)
            self.stitch_saveLocation.setDisabled(True)
            self.stitch_saveLocation_button.setDisabled(True)
            self.int_data_source.setDisabled(True)
            self.int_processed_location.setDisabled(True)
            self.int_data_source_check.setDisabled(True)
            self.int_data_folder_button.setDisabled(True)
            self.int_calib_source.setDisabled(True)
            self.int_wavelength.setDisabled(True)
            self.int_dcenterx.setDisabled(True)
            self.int_dcentery.setDisabled(True)
            self.int_detectordistance.setDisabled(True)
            self.int_detect_tilt_alpha.setDisabled(True)
            self.int_detect_tilt_delta.setDisabled(True)
            self.int_calib_folder_button.setDisabled(True)
            self.int_processed_location_folder_button.setDisabled(True)
            self.int_saveCustomCalib.setDisabled(True)
            

        def independentClicked():
            self.transformCheck.setEnabled(True)
            self.stitchCheck.setEnabled(True)
            self.integrateCheck.setEnabled(True)
            self.images_select.setEnabled(True)
            self.images_select_files_button.setEnabled(True)
            self.stitch_saveLocation.setEnabled(True)
            self.stitch_saveLocation_button.setEnabled(True)
            self.int_data_source.setEnabled(True)
            self.int_processed_location.setEnabled(True)
            self.int_data_source_check.setEnabled(True)
            self.int_data_folder_button.setEnabled(True)
            self.int_calib_source.setEnabled(True)
            self.int_wavelength.setEnabled(True)
            self.int_dcenterx.setEnabled(True)
            self.int_dcentery.setEnabled(True)
            self.int_detectordistance.setEnabled(True)
            self.int_detect_tilt_alpha.setEnabled(True)
            self.int_detect_tilt_delta.setEnabled(True)
            self.int_calib_folder_button.setEnabled(True)
            self.int_processed_location_folder_button.setEnabled(True)
            self.int_saveCustomCalib.setEnabled(True)

        self.transformCheck = QCheckBox("Transform")
        self.stitchCheck = QCheckBox("Stitch")
        self.integrateCheck = QCheckBox("Integrate") 

        def hi():
            if self.integrateCheck.isChecked():
                self.transformCheck.setChecked(True)
                self.transformCheck.setDisabled(True)
            else:
                self.transformCheck.setEnabled(True)
                self.transformCheck.setChecked(False)

        self.integrateCheck.stateChanged.connect(hi)

        self.workflow = QRadioButton("Workflow")
        self.independent = QRadioButton("Independent")
        self.workflow.setChecked(True)
        workflowClicked()
        self.workflow.clicked.connect(workflowClicked)
        self.independent.clicked.connect(independentClicked)

        
        vbox = QVBoxLayout()
        h = QHBoxLayout()
        vbox.addWidget(self.macroSelected)
        vbox.addWidget(self.tipLabel)
        vbox.addStretch()
        vbox.addWidget(self.infoLabel)
        vbox.addStretch()
        vbox.addWidget(self.checkLabel)
        hbox = QHBoxLayout()
        workflow = QVBoxLayout()
        independent = QVBoxLayout()
        workflow.addWidget(self.workflow)
        workflow.addStretch()
        workflow.addWidget(self.workflowCheckLabel)
        hbox.addLayout(workflow)
        independent.addWidget(self.independent)
        independent.addStretch()
        independent.addWidget(self.transformCheck)
        independent.addWidget(self.stitchCheck)
        independent.addWidget(self.integrateCheck)
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        hbox.addWidget(line)
        hbox.addLayout(independent)
        vbox.addLayout(hbox)
        vbox.addWidget(self.transformCheck)
        vbox.addWidget(self.stitchCheck)
        vbox.addWidget(self.integrateCheck)
        h.addLayout(vbox)
        
        self.welcome.setLayout(h)
        
    def stack1UI(self):
        self.data_label = QLabel("Current data source:")
        #self.data_source = QLineEdit("/Users/arunshriram/Documents/SLAC Internship/test")
        self.data_source = ClickableLineEdit()
        self.data_source.setFixedWidth(580)
        self.data_folder_button = QPushButton()
        self.data_folder_button.setIcon(QIcon('images/folder_select_gray.png'))
        self.data_folder_button.setIconSize(QSize(25, 25))
        self.data_folder_button.setFixedSize(25, 25)
        self.data_folder_button.setStyleSheet('border: none;')
    
        self.data_source_check = QCheckBox("I'm going to select a folder")
        self.data_source_check.setChecked(True)
    
        self.calib_label = QLabel("Current calibration file source:")
        #self.calib_source = QLineEdit("/Users/arunshriram/Documents/SLAC Internship/calib/cal_28mar18.calib")
        self.calib_source = ClickableLineEdit()
        self.calib_source.setFixedWidth(580)
        self.calib_folder_button = QPushButton()
        self.calib_folder_button.setIcon(QIcon('images/folder_select_gray.png'))
        self.calib_folder_button.setIconSize(QSize(25, 25))
        self.calib_folder_button.setFixedSize(25, 25)
        self.calib_folder_button.setStyleSheet('border: none;')        
    
        self.processed_location_label = QLabel("Current location for processed files:")
        self.processed_location = ClickableLineEdit(self.data_source.text())
        self.processed_location.setFixedWidth(580)
        self.processed_location_folder_button = QPushButton()
        self.processed_location_folder_button.setIcon(QIcon('images/folder_select_gray.png'))
        self.processed_location_folder_button.setIconSize(QSize(25, 25))
        self.processed_location_folder_button.setFixedSize(25, 25)
        self.processed_location_folder_button.setStyleSheet('border: none;')
    
        self.custom_calib_label = QLabel("Customize your calibration here: ")
        self.dcenterx_label = QLabel("Detector Center X:")
        #self.dcenterx = QLineEdit("1041.58114546")
        self.dcenterx = ClickableLineEdit()
        self.dcentery_label = QLabel("Detector Center Y:")
        #self.dcentery = QLineEdit("2206.61923488")
        self.dcentery = ClickableLineEdit()
        self.detectordistance_label = QLabel("Detector Distance:")
        #self.detectordistance = QLineEdit("2521.46747904")
        self.detectordistance = ClickableLineEdit()
        self.detect_tilt_alpha_label = QLabel("Detector Tilt Alpha:")
        #self.detect_tilt_alpha = QLineEdit("1.57624384738")
        self.detect_tilt_alpha = ClickableLineEdit()
        self.detect_tilt_delta_label = QLabel("Detector Tilt Delta:")
        #self.detect_tilt_delta = QLineEdit("-0.540278539838")
        self.detect_tilt_delta = ClickableLineEdit()
        self.wavelength_label = QLabel("Wavelength:")
        self.wavelength = ClickableLineEdit()
    
        self.saveCustomCalib = QPushButton("Save this calibration!")
        self.saveCustomCalib.setMaximumWidth(170)        
        self.addDetectorToList(self.detectorList, "PILATUS3 X 100K-A", 487, 195)
        self.addDetectorToList(self.detectorList, "PILATUS3 X 200K-A", 487, 407)
        self.addDetectorToList(self.detectorList, "PILATUS3 X 300K", 487, 619)
        self.addDetectorToList(self.detectorList, "PILATUS3 X 300K-W", 1475, 195)
        self.addDetectorToList(self.detectorList, "PILATUS3 X 1M", 981, 1043)
        self.addDetectorToList(self.detectorList, "PILATUS3 X 2M", 1475, 1679)
        self.addDetectorToList(self.detectorList, "PILATUS3 X 6M", 2463, 2527)
        self.detector_combo = QComboBox()
        for detector in self.detectorList:
            self.detector_combo.addItem(str(detector))        

        v_box1 = QVBoxLayout()
        h_box1 = QHBoxLayout()
        h_box1.addWidget(self.data_label)
        v_box1.addLayout(h_box1)
        h_box2 = QHBoxLayout()
        h_box2.addWidget(self.data_source)
        h_box2.addWidget(self.data_folder_button)
        h_box2.addWidget(self.data_source_check)        
        h_box2.addStretch()
        v_box1.addLayout(h_box2)
        v_box1.addWidget(self.calib_label)
        h_box3 = QHBoxLayout()
        h_box3.addWidget(self.calib_source)
        h_box3.addWidget(self.calib_folder_button)
        h_box3.addStretch()
        v_box1.addLayout(h_box3)
        h__box3 = QHBoxLayout()
        h__box3.addWidget(self.custom_calib_label)
        h__box3.addWidget(self.saveCustomCalib)
        h__box3.addStretch()
        v_box1.addLayout(h__box3)
        h_box4 = QHBoxLayout()
        h_box4.addWidget(self.dcenterx_label)
        h_box4.addWidget(self.dcentery_label)
        h_box4.addWidget(self.detectordistance_label)
        h_box4.addWidget(self.detect_tilt_alpha_label)
        h_box4.addWidget(self.detect_tilt_delta_label)
        h_box4.addWidget(self.wavelength_label)
        v_box1.addLayout(h_box4)
        h_box5 = QHBoxLayout()
        h_box5.addWidget(self.dcenterx)
        h_box5.addWidget(self.dcentery)
        h_box5.addWidget(self.detectordistance)
        h_box5.addWidget(self.detect_tilt_alpha)
        h_box5.addWidget(self.detect_tilt_delta)
        h_box5.addWidget(self.wavelength)
        v_box1.addLayout(h_box5)
        h = QHBoxLayout()
        h.addWidget(self.processed_location_label)
        h.addStretch()
        h.addWidget(self.detector_combo)
        v_box1.addLayout(h)
        h_box6 = QHBoxLayout()
        h_box6.addWidget(self.processed_location)
        h_box6.addWidget(self.processed_location_folder_button)
        h_box6.addStretch()
        v_box1.addLayout(h_box6)
        
        self.transformStack.setLayout(v_box1)
        
    def addDetectorToList(self, lst, name, width, height):
        det = Detector(name, width, height)
        lst.append(det)        
        
    def stack2UI(self):
        self.images_select = ClickableLineEdit()
        self.images_select.setFixedWidth(580)
        self.images_select_files_button = QPushButton()
        self.images_select_files_button.setIcon(QIcon('images/folder_select_gray.png'))
        self.images_select_files_button.setIconSize(QSize(25, 25))
        self.images_select_files_button.setFixedSize(25, 25)
        self.images_select_files_button.setStyleSheet('border: none;')
        self.saveLabel = QLabel("File Save Location:")
        #self.saveLabel.setStyleSheet("QLabel {color: white;}")
        self.stitch_saveLocation = ClickableLineEdit()
        self.stitch_saveLocation.setFixedWidth(580)
        self.stitch_saveLocation_button = QPushButton()
        self.stitch_saveLocation_button.setIcon(QIcon("images/folder_select_gray.png"))
        self.stitch_saveLocation_button.setFixedSize(25 ,25)
        self.stitch_saveLocation_button.setIconSize(QSize(25, 25))
        self.stitch_saveLocation_button.setStyleSheet("border: none;")
    
        self.stitch_data_label = QLabel("Current data folder:")
        #self.stitch_data_label.setStyleSheet("QLabel {color: white;}")
        v_box = QVBoxLayout()
        fileSelect = QHBoxLayout()
        v_box.addWidget(self.stitch_data_label)
        fileSelect.addWidget(self.images_select)
        fileSelect.addWidget(self.images_select_files_button)
        fileSelect.addStretch()
        v_box.addLayout(fileSelect)
        v_box.addWidget(self.saveLabel)
        fileSave = QHBoxLayout()
        fileSave.addWidget(self.stitch_saveLocation)
        fileSave.addWidget(self.stitch_saveLocation_button)
        fileSave.addStretch()
        v_box.addLayout(fileSave)    
       
        self.stitchStack.setLayout( v_box)
        
    def stack3UI(self):
        self.q_min_label = QLabel('Q Min:')
        #self.q_min_label.setStyleSheet("QLabel {background-color : rgb(29, 30, 50); color: white; }")
        self.q_min = ClickableLineEdit('0.0')
        self.q_min.setFixedWidth(65)
    
        self.q_max_label = QLabel('Q Max:')
        #self.q_max_label.setStyleSheet("QLabel {background-color : rgb(29, 30, 50); color: white; }")
        self.q_max = ClickableLineEdit('0.0')
        
        self.q_max.setFixedWidth(65)
    
        self.chi_min_label = QLabel("Chi min:")
        #self.chi_min_label.setStyleSheet("QLabel {background-color : rgb(29, 30, 50); color: white; }")
        self.chi_min = ClickableLineEdit('0.0')
        
        self.chi_min.setFixedWidth(65)
    
        self.chi_max_label = QLabel("Chi max:")
        #self.chi_max_label.setStyleSheet("QLabel {background-color : rgb(29, 30, 50); color: white; }")
        self.chi_max = ClickableLineEdit('0.0')
        
        self.chi_max.setFixedWidth(65)    
        
        self.int_data_label = QLabel("Current data source:")
        self.int_data_source = ClickableLineEdit()
        
        self.int_data_source.setFixedWidth(580)
        self.int_data_folder_button = QPushButton()
        self.int_data_folder_button.setIcon(QIcon('images/folder_select_gray.png'))
        self.int_data_folder_button.setIconSize(QSize(25, 25))
        self.int_data_folder_button.setFixedSize(25, 25)
        self.int_data_folder_button.setStyleSheet('border: none;')
        self.int_data_source_check = QCheckBox("I'm going to select a folder")
        #self.int_data_source_check.setStyleSheet("QCheckBox {background-color : rgb(29, 30, 50); color: white; }")
        
        self.int_data_source_check.setChecked(True)
        
        self.int_processed_location_label = QLabel("Current location for processed files:")
        self.int_processed_location = ClickableLineEdit(self.int_data_source.text())
        
        self.int_processed_location.setFixedWidth(580)
        self.int_processed_location_folder_button = QPushButton()
        self.int_processed_location_folder_button.setIcon(QIcon('images/folder_select_gray.png'))
        self.int_processed_location_folder_button.setIconSize(QSize(25, 25))
        self.int_processed_location_folder_button.setFixedSize(25, 25)
        self.int_processed_location_folder_button.setStyleSheet('border: none;')    
        
        self.int_custom_calib_label = QLabel("Customize your calibration here: ")
        self.int_dcenterx_label = QLabel("Detector Center X:")
        #self.int_dcenterx = QLineEdit("1041.58114546")
        self.int_dcenterx = ClickableLineEdit()
        
        self.int_dcentery_label = QLabel("Detector Center Y:")
        #self.int_dcentery = QLineEdit("2206.61923488")
        self.int_dcentery = ClickableLineEdit()
        
        self.int_detectordistance_label = QLabel("Detector Distance:")
        #self.int_detectordistance = QLineEdit("2521.46747904")
        self.int_detectordistance = ClickableLineEdit()
        
        self.int_detect_tilt_alpha_label = QLabel("Detector Tilt Alpha:")
        #self.int_detect_tilt_alpha = QLineEdit("1.57624384738")
        self.int_detect_tilt_alpha = ClickableLineEdit()
        
        self.int_detect_tilt_delta_label = QLabel("Detector Tilt Delta:")
        #self.int_detect_tilt_delta = QLineEdit("-0.540278539838")
        self.int_detect_tilt_delta = ClickableLineEdit()
        
        self.int_wavelength_label = QLabel("Wavelength:")
        self.int_wavelength = ClickableLineEdit()
        
        self.int_saveCustomCalib = QPushButton("Save this calibration!")
        #self.int_saveCustomCalib.setStyleSheet("QPushButton {background-color : rgb(60, 60, 60); color: white; }")
        self.int_saveCustomCalib.setMaximumWidth(170)            
        
        self.int_calib_label = QLabel("Current calibration file source:")
        self.int_calib_source = ClickableLineEdit()
        self.int_calib_source.setFixedWidth(580)
        self.int_calib_folder_button = QPushButton()
        self.int_calib_folder_button.setIcon(QIcon('images/folder_select_gray.png'))
        self.int_calib_folder_button.setIconSize(QSize(25, 25))
        self.int_calib_folder_button.setFixedSize(25, 25)
        self.int_calib_folder_button.setStyleSheet('border: none;')
      
        hbox = QHBoxLayout()
        v_box1 = QVBoxLayout()
        h1 = QHBoxLayout()
        h2 = QHBoxLayout()
        h3 = QHBoxLayout()
        h4 = QHBoxLayout()
        h1.addWidget(self.q_min_label)
        h1.addStretch()
        h1.addWidget(self.q_min)
        v_box1.addLayout(h1)
        h2.addWidget(self.q_max_label)
        h2.addStretch()
        h2.addWidget(self.q_max)
        v_box1.addLayout(h2)
        h3.addWidget(self.chi_min_label)
        h3.addStretch()
        h3.addWidget(self.chi_min)
        v_box1.addLayout(h3)
        h4.addWidget(self.chi_max_label)
        h4.addStretch()
        h4.addWidget(self.chi_max)
        v_box1.addLayout(h4)
        
        layout = QVBoxLayout()
        h_box2 = QHBoxLayout()
        h_box2.addWidget(self.int_data_source)
        #h_box2.addStretch()
        h_box2.addWidget(self.int_data_folder_button)
        h_box2.addWidget(self.int_data_source_check)
        h_box2.addStretch()
        layout.addWidget(self.int_data_label)
        layout.addLayout(h_box2)
        layout.addWidget(self.int_calib_label)
        h_box3 = QHBoxLayout()
        h_box3.addWidget(self.int_calib_source)
        #h_box3.addStretch()
        h_box3.addWidget(self.int_calib_folder_button)
        h_box3.addStretch()
        layout.addLayout(h_box3)
        layout.addWidget(self.int_custom_calib_label)
        h_box5 = QHBoxLayout()
        h_box5.addWidget(self.int_dcenterx_label)
        h_box5.addWidget(self.int_dcentery_label)
        h_box5.addWidget(self.int_detectordistance_label)
        h_box5.addWidget(self.int_detect_tilt_alpha_label)
        h_box5.addWidget(self.int_detect_tilt_delta_label)
        h_box5.addWidget(self.int_wavelength_label)    
        layout.addLayout(h_box5)
        h_box6 = QHBoxLayout()
        h_box6.addWidget(self.int_dcenterx)
        h_box6.addWidget(self.int_dcentery)
        h_box6.addWidget(self.int_detectordistance)
        h_box6.addWidget(self.int_detect_tilt_alpha)
        h_box6.addWidget(self.int_detect_tilt_delta)
        h_box6.addWidget(self.int_wavelength)
        layout.addLayout(h_box6)
        layout.addWidget(self.int_saveCustomCalib)
        h_box7 = QHBoxLayout()
        h_box7.addWidget(self.int_processed_location)
        h_box7.addWidget(self.int_processed_location_folder_button)
        h_box7.addStretch()
        layout.addWidget(self.int_processed_location_label)
        layout.addLayout(h_box7)
        
        hbox.addLayout(layout)
        hbox.addStretch()
        hbox.addLayout(v_box1)
        self.integrateStack.setLayout(hbox)
     
     

    def updateConnections(self):
        self.cancelButton.clicked.connect(lambda: self.close())
        self.loadMacroButton.clicked.connect(self.loadMacro)
        self.addToQueueButton.clicked.connect(lambda: addMacroToQueue(self.windowreference))
        self.saveCustomCalib.clicked.connect(self.saveCalibAction)
        self.int_saveCustomCalib.clicked.connect(self.saveIntCalibAction)
        self.data_folder_button.clicked.connect(self.getTransformDataSourceDirectoryPath)
        self.int_data_folder_button.clicked.connect(self.getIntegrateDataSourceDirectoryPath)
        self.calib_folder_button.clicked.connect(self.getCalibSourcePath)
        self.int_calib_folder_button.clicked.connect(self.getIntCalibSourcePath)
        self.processed_location_folder_button.clicked.connect(self.setProcessedLocation)        
        self.int_processed_location_folder_button.clicked.connect(self.setIntProcessedLocation)
        self.saveButton.clicked.connect(self.saveMacro)
        self.stackList.currentRowChanged.connect(self.display)
        self.images_select_files_button.clicked.connect(self.stitchImageSelect)
        self.stitch_saveLocation_button.clicked.connect(self.setStitchSaveLocation)
        
        for editor in self.findChildren(ClickableLineEdit):
            editor.textChanged.connect(lambda: self.setFieldsChanged(True))
        for box in self.findChildren(QCheckBox):
            if box != self.data_source_check:
                box.stateChanged.connect(lambda: self.setFieldsChanged(True))        
        self.detector_combo.currentIndexChanged.connect(lambda: self.setFieldsChanged(True))
        
    
    def setStitchSaveLocation(self):
        path = str(QFileDialog.getExistingDirectory(self, "Select a location for processed files"))
        if path !='':
            self.stitch_saveLocation.setText(path)
            
    def stitchImageSelect(self):
        try:
            folderpath = str(QFileDialog.getExistingDirectory(directory=os.getcwd()))
            if folderpath != '':
                self.images_select.setText(folderpath)
                self.stitch_saveLocation.setText(folderpath)
                self.s_files_to_process = [folderpath]
        except:
            displayError(self, "Something went wrong when trying to open your directory.")
            return
    
    def setFieldsChanged(self, boo):
        self.fieldsChanged = boo
        
    def getTransformDataSourceDirectoryPath(self):
        if self.data_source_check.isChecked():
            try:
                folderpath = str(QFileDialog.getExistingDirectory())
                if folderpath != '':
                    self.data_source.setText(folderpath)
                    self.data_label.setText("Current data source:")
                    self.processed_location.setText(os.path.join(str(self.data_source.text()),   "Processed_Transform"))
                    self.t_files_to_process = [folderpath]
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
                    self.data_source.setText(os.path.dirname(filenames[0]))
                self.processed_location.setText(os.path.join(str(self.data_source.text())  , "Processed_Transform"))
                self.t_files_to_process = filenames   
            except:
                #traceback.print_exc()
                self.addToConsole("Something went wrong when trying to select your files.")
    
    def getIntegrateDataSourceDirectoryPath(self):
        if self.int_data_source_check.isChecked():
            try:
                folderpath = str(QFileDialog.getExistingDirectory())
                if folderpath != '':
                    self.int_data_source.setText(folderpath)
                    self.int_data_label.setText("Current data source:")
                    self.int_processed_location.setText(os.path.join(str(self.data_source.text()), "Processed_Integrate"))
                    self.i_files_to_process = [folderpath]
            except: 
                self.addToConsole("Something went wrong when trying to open your directory.")
        else:
            try:
           
                filenames = QFileDialog.getOpenFileNames(self, "Select the files you wish to use.")
                filenames = [str(filename) for  filename in filenames]
                if len(filenames) < 2:
                    self.int_data_label.setText("Current data source: %s" % os.path.basename(filenames[0]))
                else:    
                    self.int_data_label.setText("Current data source: (multiple files)")
                self.int_data_source.setText(os.path.dirname(filenames[0]))
                self.int_processed_location.setText(os.path.join(str(self.data_source.text()), "Processed_Integrate"))
                self.i_files_to_process = filenames   
            except:
                #traceback.print_exc()
                self.addToConsole("Something went wrong when trying to select your files.")
        
    def getCalibSourcePath(self):
        path = str(QFileDialog.getOpenFileName(self, "Select Calibration File", ('/Users/arunshriram/Documents/SLAC Internship/monhitp-gui/calib/')))
        if path !='':
            self.calib_source.setText(path)
            self.loadCalibration()
            
    def getIntCalibSourcePath(self):
        path = str(QFileDialog.getOpenFileName(self, "Select Calibration File", ('/Users/arunshriram/Documents/SLAC Internship/monhitp-gui/calib/')))
        if path !='':
            self.int_calib_source.setText(path)
            self.loadCalibration()    
            
    def setProcessedLocation(self):
        path = str(QFileDialog.getExistingDirectory(self, "Select a location for processed files", str(self.data_source.text())))
        #path = str(QFileDialog.getOpenFileName(self, "Select Calibration File", ('/Users/arunshriram/Documents/SLAC Internship/monhitp-gui/calib/')))
        if path !='':
            self.processed_location.setText(path)
        
    def setIntProcessedLocation(self):
        path = str(QFileDialog.getExistingDirectory(self, "Select a location for processed files", str(self.int_data_source.text())))
        #path = str(QFileDialog.getOpenFileName(self, "Select Calibration File", ('/Users/arunshriram/Documents/SLAC Internship/monhitp-gui/calib/')))
        if path !='':
            self.int_processed_location.setText(path)
     
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
            self.addToConsole("Calibration not saved!")
            return        
        
    def saveIntCalibAction(self):
        name = ('/Users/arunshriram/Documents/SLAC Internship/monhitp-gui/calib/cal-%s.calib') %(datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S'))
        fileName = QFileDialog.getSaveFileName(self, 'Save your new custom calibration!', name)
        try:
            with open(fileName, 'w') as calib:
                for i in range(6):
                    calib.write('-\n')
                calib.write("bcenter_x=" + str(self.int_dcenterx.text()) + '\n')
                calib.write("bcenter_y=" + str(self.int_dcentery.text()) + '\n')
                calib.write("detect_dist=" + str(self.int_detectordistance.text()) + '\n')
                calib.write("detect_tilt_alpha=" + str(self.int_detect_tilt_alpha.text()) + '\n')
                calib.write("detect_tilt_delta=" + str(self.int_detect_tilt_delta.text()) + '\n')
                calib.write("wavelength=" + str(self.int_wavelength.text()) + '\n')
                calib.write('-\n')
            self.int_calib_source.setText(os.path.expanduser(str(fileName)))
        except:
            self.addToConsole("Calibration not saved!")
            return        
    
    def addToConsole(self, message):
        self.windowreference.addToConsole(message)
        
    def saveMacro(self):
        # CHECKING VALUES TO MAKE SURE EVERYTHING IS OKAY BEFORE MACRO CAN BE SAVED
        calib_source = str(self.calib_source.text())
        dx = len(str(self.dcenterx.text()))
        dy = len(str(self.dcentery.text()))
        dd = len(str(self.detectordistance.text()))
        wav = len(str(self.wavelength.text()))
        da = len(str(self.detect_tilt_alpha.text()))
        dp = len(str(self.detect_tilt_delta.text()))
        if (not os.path.exists(calib_source)) or dp == 0 or dy == 0 or dx == 0 or dd == 0 or wav == 0 or da == 0:
            displayError(self, "Was not able to locate calibration information.")
            return

        # Checking Q and Chi Ranges

        try:
            QRange = (float(str(self.q_min.text())), float(str(self.q_max.text())))
            #            ChiRange = (config['ChiMin'],config['ChiMax'])
            ChiRange = (float(str(self.chi_min.text())), float(str(self.chi_max.text())))    
            if abs(QRange[1]-QRange[0]) < .01:
                displayError(self, "Please select a more reasonable Q range.")
                return  
            if abs(ChiRange[1] - ChiRange[0]) < 0.1:  
                displayError(self, "Please select a more reasonable Chi range.")
                return        
        except:
            displayError(self, "Please make sure you enter appropriate Q and Chi range values!")
            return

        if str(self.processed_location.text()) == "":
            self.processed_location.setText(os.path.join(str(self.data_source.text()), "Processed_Transform"))
           

        if self.t_files_to_process == []:
            self.t_files_to_process = [str(self.data_source.text())]
            t_filenames = self.t_files_to_process
        else:
            t_filenames = self.t_files_to_process    
        t_calib_source = str(self.calib_source.text())
        macrodict = {"t_calib_source": t_calib_source}

        data_source = str(self.data_source.text())
        if self.data_source_check.isChecked() and os.path.isfile(self.t_files_to_process[0]):
            displayError(self, "Please either check the \"I'm going to select a folder\" option or select at least one file.")
            return
        elif not self.data_source_check.isChecked() and os.path.isdir(self.t_files_to_process[0]):
            displayError(self, "Please either check the \"I'm going to select a folder\" option or select at least one file.")
            return
        if data_source == "":
            displayError(self, "Please select a transform data source!")
            return
       
            
        macrodict["t_data_source"] = t_filenames
        detector = str(self.detector_combo.currentText())
        macrodict["detector_type"] = detector[:detector.index(":")]
        t_proc_dir = str(self.processed_location.text())
        macrodict["t_proc_dir"] = t_proc_dir
        macrodict['transform'] = True

        # End of information checking *********************************

        # File saving ********************************
        current = os.getcwd()
        final_dir = os.path.join(current, r'macros')
        if not os.path.exists(final_dir):
            os.makedirs(final_dir)
                
        cur_time = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        name = (final_dir + '/macro-%s.csv') %(cur_time)        
        fileName = QFileDialog.getSaveFileName(self, 'Save your new macro!', name)
        fileName = str(fileName)
        if fileName == '':
            self.raise_()
            return
        # If anything else is changed after this, the editor won't let you add to the queue without saving again
        self.setFieldsChanged(False)

        # If the user is editing a workflow: ****************

        # *******************WORKFLOW***********************

        workflow = self.workflow.isChecked()
        macrodict["workflow"]  = workflow
        if workflow:
            # macrodict will have the following keys: t_data_source, detector_type, t_proc_dir, chimin, chimax, qmin, qmax, workflow
            macrodict["chimin"] = float(str(self.chi_min.text()))
            macrodict["chimax"] = float(str(self.chi_max.text()))
            macrodict["qmin"] = float(str(self.q_min.text()))
            macrodict["qmax"] = float(str(self.q_max.text()))

            with open(fileName, 'wb') as macro:
                writer = csv.writer(macro)
                for key, value in macrodict.items():
                    writer.writerow([key, value])
                
            self.curMacro = Macro(fileName, macrodict)
            self.macroSelected.setText("Current macro selected: %s" % (os.path.join(os.path.dirname(fileName).split("/")[-1], os.path.basename(fileName))))
            return

        # If the user is editing individual actions: ***************

        #*******************INDEPENDENT********************

        transform = self.transformCheck.isChecked()
        stitch = self.stitchCheck.isChecked()
        integrate = self.integrateCheck.isChecked()
        if not transform and not stitch and not integrate:
            displayError(self, "Please select either Transform, Stitch, or Integrate!")        
            return
        if transform and not os.path.exists(str(self.data_source.text())):
            displayError(self, "Please select an existing transform data source directory.")
            return
        else:
            self.t_files_to_process = [str(self.data_source.text())]
        if integrate and not os.path.exists(str(self.int_data_source.text())):
            displayError(self, "Please select an existing integrate data source directory.")
            return
        else:
            self.i_files_to_process = [str(self.int_data_source.text())]
        if stitch and not os.path.exists(str(self.images_select.text())):
            displayError(self, "Please select an existing stitch data source directory.")
            return
        if str(self.calib_source.text()) == '':
            displayError(self, "Please make sure you select a calibration source or save your custom calibration!")
            return        
       
    
        macrodict = {"transform" : transform, "stitch" : stitch, "integrate" : integrate}
    
            
        if stitch:
            macrodict["s_data_source"] = str(self.images_select.text())
            macrodict["s_proc_dir"] = str(self.stitch_saveLocation.text())
        
        if integrate:
            i_filenames = []    
            i_calib_source = str(self.int_calib_source.text())
            macrodict["i_calib_source"] = i_calib_source
            if os.path.isfile(self.i_files_to_process[0]):
                i_filenames += self.i_files_to_process
            else:
                i_filenames = [str(self.int_data_source.text())]
                
            macrodict["i_data_source"] = i_filenames
            i_proc_dir = str(self.int_processed_location.text())
            macrodict["i_proc_dir"] = i_proc_dir            
            i_calib_source = str(self.int_calib_source.text())
            
            macrodict["chimin"] = float(str(self.chi_min.text()))
            macrodict["chimax"] = float(str(self.chi_max.text()))
            macrodict["qmin"] = float(str(self.q_min.text()))
            macrodict["qmax"] = float(str(self.q_max.text()))
 
     
        with open(fileName, 'wb') as macro:
            writer = csv.writer(macro)
            for key, value in macrodict.items():
                writer.writerow([key, value])
                
        self.curMacro = Macro(fileName, macrodict)
        self.macroSelected.setText("Current macro selected: %s" % (os.path.join(os.path.dirname(fileName).split("/")[-1], os.path.basename(fileName))))
            
    
    def loadMacro(self):
        current = os.getcwd()
        final_dir = os.path.join(current, r'macros')
        if os.path.exists(final_dir):
            filename = QFileDialog.getOpenFileName(self, "Select your macro", directory=final_dir)
        else:   
            filename = QFileDialog.getOpenFileName(self, "Select your macro", directory=current)
        
        filename = str(filename)
        transform = stitch = integrate = False
        try:
            with open(filename, 'rb') as macro:
                reader = csv.reader(macro)
                macrodict = dict(reader)
            self.curMacro = Macro(filename, macrodict)
            transform = "True" in macrodict['transform']
            stitch = "True" in macrodict['stitch']
            integrate = "True" in macrodict['integrate']
            if transform:
                try:
                    macrodict['t_data_source'] = ast.literal_eval(macrodict['t_data_source'])
                except:
                    pass
                t_data_source = macrodict['t_data_source']
                t_calib_source = macrodict['t_calib_source']
                t_proc_dir = macrodict['t_proc_dir']
                if os.path.isdir(t_data_source[0]):
                    self.t_files_to_process = t_data_source
                    self.data_label.setText("Current data source: %s" % os.path.basename(t_data_source[0]))
                    self.data_source.setText(t_data_source[0])
                elif os.path.isfile(t_data_source[0]):
                    self.t_files_to_process = t_data_source
                    self.data_label.setText("Current data source: (multiple files)")                        
                    self.data_source.setText(os.path.dirname(t_data_source[0]))
                else:
                    displayError(self.windowreference, "Could not locate transform data source specified in macro!")
                    QApplication.processEvents()
                    return                    
                if os.path.exists(t_calib_source):
                    self.calib_source.setText(t_calib_source)
                    self.loadCalibration()
                else:
                    displayError(self.windowreference, "Could not locate transform calibration source specified in macro!")
                    QApplication.processEvents()
                    return                
                if os.path.exists(t_proc_dir):
                    self.processed_location.setText(t_proc_dir)
                else:
                    self.processed_location.setText(t_data_source)
                detector = macrodict['detector_type']
                index = 0
                for i in range(len(self.detectorList)):
                    if self.detectorList[i].getName() == detector:
                        index = i
                        break
                self.detector_combo.setCurrentIndex(index)
                    
            if integrate:
                try:
                    macrodict['i_data_source'] = ast.literal_eval(macrodict['i_data_source'])
                except:
                    pass                
                i_data_source = macrodict['i_data_source']
                i_calib_source = macrodict['i_calib_source']
                i_proc_dir = macrodict['i_proc_dir']
                if os.path.isdir(i_data_source[0]):
                    self.i_files_to_process = i_data_source
                    self.int_data_label.setText("Current data source: %s" % os.path.basename(i_data_source[0]))
                    self.int_data_source.setText(i_data_source[0])            
                elif os.path.sifile(i_data_source[0]):
                    self.i_files_to_process = i_data_source
                    self.int_data_label.setText("Current data source: (multiple files)")                        
                    self.int_data_source.setText(os.path.dirname(i_data_source[0]))
                        
                else:
                    displayError(self.windowreference, "Could not locate integrate data source specified in macro!")
                    return
                if os.path.exists(i_calib_source):
                    self.calib_source.setText(i_calib_source)
                    self.loadCalibration()
                else:
                    displayError(self.windowreference, "Could not locate integrate calibration source specified in macro!")
                    QApplication.processEvents()
                    return                    
                if os.path.exists(i_proc_dir):
                    self.processed_location.setText(i_proc_dir)
                else:
                    self.processed_location.setText(i_data_source)                
                self.q_min.setText(macrodict['qmin'])
                self.q_max.setText(macrodict['qmax'])
                self.chi_min.setText(macrodict['chimin'])
                self.chi_max.setText(macrodict['chimax'])
            if stitch:
                s_data_source = macrodict['s_data_source']
                s_proc_dir = macrodict['s_proc_dir']
                if os.path.exists(s_data_source):
                    self.images_select.setText(s_data_source)
                if os.path.exists(s_proc_dir):
                    self.stitch_saveLocation.setText(s_proc_dir)
                else:
                    self.stitch_saveLocation.setText(s_data_source)
                    
            self.transformCheck.setChecked(transform)
            self.stitchCheck.setChecked(stitch)
            self.integrateCheck.setChecked(integrate)
            self.macroSelected.setText("Current macro selected: %s" % (os.path.join(os.path.dirname(str(filename)).split("/")[-1], os.path.basename(str(filename)))))
            if self.data_source_check.isChecked():
                self.data_label.setText("Current data source:")
     
            
            self.setFieldsChanged(False)
          
                                 
        except:
            traceback.print_exc()
            displayError(self, "Unable to load macro!")
                 
            
    def loadCalibration(self):
        if str(self.calib_source.text()) != '':
            try:
                d_in_pixel, Rotation_angle, tilt_angle, lamda, x0, y0 = parse_calib(str(self.calib_source.text()))
            except:
                #self.console.append("Unable to locate calibration source file.")
                return
            self.wavelength.setText(str(lamda))
            self.detectordistance.setText(str(d_in_pixel))
            self.dcenterx.setText(str(x0))
            self.dcentery.setText(str(y0))
            self.detect_tilt_alpha.setText(str(Rotation_angle))
            self.detect_tilt_delta.setText(str(tilt_angle))
        if str(self.int_calib_source.text()) != '':
            try:
                d_in_pixel, Rotation_angle, tilt_angle, lamda, x0, y0 = parse_calib(str(self.int_calib_source.text()))
            except:
                #self.console.append("Unable to locate calibration source file.")
                return
            self.int_wavelength.setText(str(lamda))
            self.int_detectordistance.setText(str(d_in_pixel))
            self.int_dcenterx.setText(str(x0))
            self.int_dcentery.setText(str(y0))
            self.int_detect_tilt_alpha.setText(str(Rotation_angle))
            self.int_detect_tilt_delta.setText(str(tilt_angle))        
            

def generateQueueWidgets(self):
    self.queue = QListWidget()
    self.queue.setFont(QFont("Avenir", 16))
    self.queue.setStyleSheet("background-color: rgba(34, 200, 157, 200);")
    self.queue.setMaximumHeight(500)
    self.addMacroButton = QPushButton(" + ")
    self.addMacroButton.setStyleSheet("QPushButton {background-color : rgb(60, 60, 60); color: white; }")
    self.removeButton = QPushButton(" - ")
    self.removeButton.setStyleSheet("QPushButton {background-color : rgb(60, 60, 60); color: white; }")
    self.qconsole = QTextBrowser()
    self.qconsole.setMinimumHeight(150)
    self.qconsole.setMaximumHeight(300)
    self.qconsole.moveCursor(QTextCursor.End)

    self.qconsole.setFont(QFont("Avenir", 14))
    self.qconsole.setStyleSheet("margin:3px; border:1px solid rgb(0, 0, 0); background-color: rgb(240, 255, 240);")           
    self.startQueueButton = QPushButton("Start queue")
    self.startQueueButton.setFixedWidth(170)
    self.startQueueButton.setFixedHeight(30)
    self.startQueueButton.setStyleSheet("background-color: rgb(100, 215, 76);")
    
    self.queue_bar_files = QRoundProgressBar()
    self.queue_bar_files.setFixedSize(150, 150)
    self.queue_bar_files.setDataPenWidth(.01)
    self.queue_bar_files.setOutlinePenWidth(.01)
    self.queue_bar_files.setDonutThicknessRatio(0.85)
    self.queue_bar_files.setDecimals(1)
    self.queue_bar_files.setFormat('%p %')
    self.queue_bar_files.setNullPosition(90)
    self.queue_bar_files.setBarStyle(QRoundProgressBar.StyleDonut)
    self.queue_bar_files.setDataColors([(0, QColor(qRgb(34, 200, 157))), (1, QColor(qRgb(34, 200, 157)))])
    self.queue_bar_files.setRange(0, 100)
    self.queue_bar_files.setValue(0)    
    
    self.queue_bar = QRoundProgressBar()
    self.queue_bar.setFixedSize(150, 150)
    self.queue_bar.setDataPenWidth(.01)
    self.queue_bar.setOutlinePenWidth(.01)
    self.queue_bar.setDonutThicknessRatio(0.85)
    self.queue_bar.setDecimals(1)
    self.queue_bar.setFormat('%p %')
    self.queue_bar.setNullPosition(90)
    self.queue_bar.setBarStyle(QRoundProgressBar.StyleDonut)
    self.queue_bar.setDataColors([(0, QColor(qRgb(34, 200, 157))), (1, QColor(qRgb(34, 200, 157)))])
    self.queue_bar.setRange(0, 100)
    self.queue_bar.setValue(0)        
    
    self.queue_bar_files_label = QLabel("Percentage of current process completed")
    self.queue_bar_files_label.setFont(QFont("Avenir", 16))
    self.queue_bar_files_label.setStyleSheet("QLabel {color: rgb(34, 200, 157);}")
    self.queue_bar_label = QLabel("Percentage of current macro completed")
    self.queue_bar_label.setFont(QFont("Avenir", 16))
    self.queue_bar_label.setStyleSheet("QLabel {color: rgb(34, 200, 157);}")

    
def generateQueueLayout(self):
    v_box = QVBoxLayout()
    add_remove_box = QHBoxLayout()
    v_box.addWidget(self.queue)
    add_remove_box.addWidget(self.addMacroButton)
    add_remove_box.addWidget(self.removeButton)
    add_remove_box.addStretch()
    v_box.addLayout(add_remove_box)
    v_box.addWidget(self.startQueueButton)
    v1 = QVBoxLayout()
    v2 = QVBoxLayout()
    barfilesbox = QHBoxLayout()
    barfilesbox.addStretch()
    barfilesbox.addWidget(self.queue_bar_files)
    v1.addLayout(barfilesbox)
    v1.addWidget(self.queue_bar_files_label)
    v1.setSpacing(0)
    
    v2.addWidget(self.queue_bar)
    v2.addWidget(self.queue_bar_label)
    v2.setSpacing(0)
    
    line = QFrame()
    line.setFrameShape(QFrame.VLine)
    line.setStyleSheet("QFrame {color: rgb(34, 200, 157);}")
    
    h = QHBoxLayout()
    h.addStretch()
    h.addLayout(v1)
    h.addWidget(line)
    h.addLayout(v2)
    h.addStretch()
    v_box.addLayout(h)
    
  
    v_box.addWidget(self.qconsole)
    return v_box


def beginQueue(self):
    if len(self.macroQueue) < 1:
        self.addToConsole("No elements in the queue!")
        return
    self.addToConsole("*****************************************************************")
    self.addToConsole("**********************Beginning Queue...************************")
    self.addToConsole("*****************************************************************")
    count = 0
    for mac in self.macroQueue:
        if mac.isWorkflow():
            count = 3
        else:
            if mac.shouldTransform():
                count +=1
            if mac.shouldStitch():
                count += 1
            if mac.shouldIntegrate():
                count += 1
    increment = (1/float(count))*100
    progress = 0
    self.queue_bar.setValue(progress)
    macrindex = 0
    self.disableWidgets()
    for macro in self.macroQueue:
        self.queue.setCurrentIndex(macrindex)
        self.addToConsole("Processing %s..." % os.path.basename(str(macro.getFilename())))
        curFileCount = 0
        if macro.isWorkflow():

            #  ************ TRANSFORM PROCESSING ******************

            processed_filedir = macro.getTProcessedFileDir()
            calib_source = macro.getTCalibInfo()
            detectorData = macro.getDetectorData()
            dataFiles = macro.getTDataFiles()
            QRange = macro.getQRange()
            ChiRange = macro.getChiRange()
            startTransformThread(self, dataFiles, calib_source, detectorData, processed_filedir)
            while self.processDone == False:
                time.sleep(.2)
                QApplication.processEvents()
            time.sleep(1.5) # let the user have a chance to look at the graph lol
            progress += increment
            self.queue_bar.setValue(progress)
            
            # **************** STITCH PROCESSING *********************

            dataFiles = [processed_filedir]    

            s_processed_filedir = os.path.join(processed_filedir, "Processed_Stitch")    
            
            startStitchThread(self, dataFiles[0], s_processed_filedir)
            while self.processDone == False:
                time.sleep(.2)
                QApplication.processEvents()     
            time.sleep(1.5)
                
            progress += increment
            self.queue_bar.setValue(progress)            

            # **************** INTEGRATE PROCESSING **************

            dataFiles = [processed_filedir]
            i_processed_filedir = os.path.join(processed_filedir ,"Processed_Integrate"    )

            startIntegrateThread(self, dataFiles, calib_source, detectorData, i_processed_filedir, QRange, ChiRange)
            progress += increment
            self.queue_bar.setValue(progress)
        else:

            if macro.shouldTransform():
                processed_filedir = macro.getTProcessedFileDir()
                calib_source = macro.getTCalibInfo()
                detectorData = macro.getDetectorData()
                dataFiles = macro.getTDataFiles()
                startTransformThread(self, dataFiles, calib_source, detectorData, processed_filedir)     
                while self.processDone == False:
                    time.sleep(.2)
                    QApplication.processEvents()
                time.sleep(1.5) # let the user have a chance to look at the graph lol
                progress += increment
                self.queue_bar.setValue(progress)
                        
                
            if macro.shouldStitch():
                processed_filedir = macro.getSProcessedFileDir()
                dataFiles = macro.getSDataFiles()            
                startStitchThread(self, dataFiles, processed_filedir)
                while self.processDone == False:
                    time.sleep(.2)
                    QApplication.processEvents()     
                time.sleep(1.5)
                    
                progress += increment
                self.queue_bar.setValue(progress)            
            
            if macro.shouldIntegrate():
                processed_filedir = macro.getIProcessedFileDir()
                calib_source = macro.getICalibInfo()
                detectorData = macro.getDetectorData()
                dataFiles = macro.getIDataFiles() 
                QRange = macro.getQRange()
                ChiRange = macro.getChiRange()
                startIntegrateThread(self, dataFiles, calib_source, detectorData, processed_filedir, QRange, ChiRange )         
                progress += increment
                self.queue_bar.setValue(progress)
        macrindex += 1
    self.enableWidgets()

# list str tuple str -> None
# Takes a list of datafiles (either a list with a string folder name inside or a list of pathnames), a calibration source, a tuple of detector data, and a processed file directory, and starts the transform thread.
def startTransformThread(self, dataFiles, calib_source, detectorData, processed_filedir):
    self.setCurrentIndex(0)
    self.addToConsole('******************************************************************************')
    self.addToConsole('************************ Beginning Transform Processing... ***********************')
    self.addToConsole('******************************************************************************')            
    self.addToConsole('Calibration File: ' + calib_source)
    if os.path.isfile(dataFiles[0]):
        self.addToConsole('Folder to process: ' + os.path.dirname(dataFiles[0]))
    else:
        self.addToConsole("Folder to process: " + dataFiles[0])
    self.addToConsole('')        
    # TransformThread: __init__(self, windowreference, processedPath, calibPath, dataPath, detectorData, files_to_process):
    self.transformThread = TransformThread(self, processed_filedir, calib_source, detectorData, dataFiles)
    self.transformThread.setAbortFlag(False)
    self.abort.clicked.connect(self.transformThread.abortClicked)
    self.int_abort.clicked.connect(self.transformThread.abortClicked) # Making sure that the connections are valid for the current instance of TransformThread.
    self.connect(self.transformThread, SIGNAL("addToConsole(PyQt_PyObject)"), self.addToConsole)
    self.connect(self.transformThread, SIGNAL("setRawImage(PyQt_PyObject)"), self.setRawImage)
    self.connect(self.transformThread, SIGNAL("enableWidgets()"), self.enableWidgets)
    self.connect(self.transformThread, SIGNAL("bar(int, PyQt_PyObject)"), self.setRadialBar)
    self.connect(self.transformThread, SIGNAL("enable()"), self.enableWidgets)
    self.connect(self.transformThread, SIGNAL("finished(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), self.done)
    self.processDone = False
    self.transformThread.start()        
    
# list str -> None
# Takes a list of data files (either a list with a string folder name inside or a list of pathnames), and a processed file directory, and starts the stitch thread
def startStitchThread(self, dataFiles, processed_filedir):
    self.setCurrentIndex(1)
    self.disableWidgets()
    QApplication.processEvents()
    #self.console.clear()
    self.addToConsole('****************************************************')
    self.addToConsole('********** Beginning Stitch Processing... ***********')
    self.addToConsole('****************************************************')
    QApplication.processEvents()
    

    self.stitchThread = StitchThread(self, dataFiles, processed_filedir)
    #self.stitchThread.setAbortFlag(False)
    # make sure that if the abort button is clicked, it is aborting the current running stitch thread, so this needs to be run for every new stitch thread
    self.stitchThread.setAbortFlag(False)
    self.stitch_abort.clicked.connect(self.stitchThread.abortClicked)
    
    # these connections are the only way the thread can communicate with the MONster
    self.connect(self.stitchThread, SIGNAL("addToConsole(PyQt_PyObject)"), self.addToConsole)
    self.connect(self.stitchThread, SIGNAL("bar(int, PyQt_PyObject)"), self.setRadialBar)
    self.connect(self.stitchThread, SIGNAL("finished(PyQt_PyObject, PyQt_PyObject)"), ms.stitchDone)
    self.connect(self.stitchThread, SIGNAL("setImage(PyQt_PyObject, PyQt_PyObject)"), ms.setStitchImage)
    self.connect(self.stitchThread, SIGNAL("resetStitch(PyQt_PyObject)"), ms.resetStitch)
    self.stitchThread.start()        
    self.processDone = False

# list str tuple str tuple tuple-> None
# Takes a list of datafiles (either a list with a string folder name inside or a list of pathnames), a calibration source, a tuple of detector data, a processed file directory, a Q Range, and a Chi Range, and starts the integrate thread.
def startIntegrateThread(self, dataFiles, calib_source, detectorData, processed_filedir, QRange, ChiRange):
    self.setCurrentIndex(2)
    self.addToConsole('******************************************************************************')
    self.addToConsole('********************* Beginning Integration Processing... *********************')
    self.addToConsole('******************************************************************************')            
    QApplication.processEvents()
    self.integrateThread = IntegrateThread(self, calib_source, processed_filedir, detectorData, dataFiles, (QRange, ChiRange))
    self.integrateThread.setAbortFlag(False)
    self.int_abort.clicked.connect(self.integrateThread.abortClicked)
    
    self.connect(self.integrateThread, SIGNAL("addToConsole(PyQt_PyObject)"), self.addToConsole)
    self.connect(self.integrateThread, SIGNAL("enableWidgets()"), self.enableWidgets)
    self.connect(self.integrateThread, SIGNAL("set1DImage(PyQt_PyObject, PyQt_PyObject)"), mi.set1DImage)
    self.connect(self.integrateThread, SIGNAL("finished(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), self.done)
    self.connect(self.integrateThread, SIGNAL("enable()"), self.enableWidgets)
    self.integrateThread.start()            
        
# returns the number of files specified either by the dataFiles or the data source passed in
def calculateBarIncrement(dataFiles, dataSource):
    num_files = 0
    if os.path.isdir(dataFiles[0]):
        fileList = sorted(glob.glob(os.path.join(dataSource, '*.tif')))
        files = fileList[0:10000000000000000]         
        try: # need a try block in case len(files) comes out to zero
            num_files = (1/float(len(files)))*100
        except:
            num_files = 0
            # No need to tell user that the data source has no files, since TransformThread will take care of that later. Just
            # need to make sure that the radial progress bar doesn't increase, as there are no files to process
    else:
        num_files = (1/float(len(dataFiles)))*100    
    return num_files
    
def addMacroToQueue(self):
    global curIndex

    try:
        if self.editor.curMacro.isWorkflow():
            if self.editor.fieldsChanged == True:
                displayError(self, "Please save your macro!")
                return
            try:
                QRange = (float(str(self.editor.q_min.text())), float(str(self.editor.q_max.text())))
                #            ChiRange = (config['ChiMin'],config['ChiMax'])
                ChiRange = (float(str(self.editor.chi_min.text())), float(str(self.editor.chi_max.text())))    
                if abs(QRange[1]-QRange[0]) < .01:
                    displayError(self, "Please select a more reasonable Q range.")
                    return  
                if abs(ChiRange[1] - ChiRange[0]) < 0.1:  
                    displayError(self, "Please select a more reasonable Chi range.")
                    return        
            except:
                displayError(self, "Please make sure you enter appropriate Q and Chi range values!")
                return
            macro = QListWidgetItem("Process %s: Added macro \"%s\"" % (curIndex, os.path.basename(str(self.editor.curMacro.getFilename()))))
        
            self.macroQueue.append( self.editor.curMacro )     
        else:
            if not self.editor.integrateCheck.isChecked() and not self.editor.transformCheck.isChecked() and not self.editor.stitchCheck.isChecked():
                displayError(self, "Select at least one of the following: Transform, Stitch, or Integrate.")
                return
            if self.editor.fieldsChanged == True:
                displayError(self, "Please save your macro!")
                return
            if self.editor.integrateCheck.isChecked():
                try:
                    QRange = (float(str(self.editor.q_min.text())), float(str(self.editor.q_max.text())))
                    #            ChiRange = (config['ChiMin'],config['ChiMax'])
                    ChiRange = (float(str(self.editor.chi_min.text())), float(str(self.editor.chi_max.text())))    
                    if abs(QRange[1]-QRange[0]) < .01:
                        displayError(self, "Please select a more reasonable Q range.")
                        return  
                    if abs(ChiRange[1] - ChiRange[0]) < 0.1:  
                        displayError(self, "Please select a more reasonable Chi range.")
                        return        
                except:
                    displayError(self, "Please make sure you enter appropriate Q and Chi range values!")
                    return
            macro = QListWidgetItem("Process %s: Added macro \"%s\"" % (curIndex, os.path.basename(str(self.editor.curMacro.getFilename()))))
            
            self.macroQueue.append( self.editor.curMacro )        
    except: # Almost always raised when the user tries to save a macro before saving, so self.editor.curMacro is None
        displayError(self, "Please make sure you save your macro!")
        #self.editor.raise_()
        return
        
    curIndex+= 1
    self.queue.addItem(macro)
    self.editor.close()
    QApplication.processEvents()

def addMacro(self):
    self.editor.show()
    self.editor.raise_()

def removeMacro(self):
    global curIndex
    if len(self.queue.selectedItems()) > 0:
        index = self.queue.currentRow()
        self.queue.takeItem(index)
        #print("Removing item: %s" % self.macroQueue[index])
        del self.macroQueue[index]        
        #print("Current macro queue: ")
        #for i in range(len(self.macroQueue)):
            #print(("%s, " % self.macroQueue[i].getFilename()))        
        itemsTextList = [str(self.queue.item(i).text()) for i in range(self.queue.count())]
        for i in range(len(itemsTextList) ):
            process_number = itemsTextList[i].split(':')
            self.queue.item(i).setText(("Process %s: " % (i + 1) ) + process_number[1])
        curIndex = len(itemsTextList) + 1