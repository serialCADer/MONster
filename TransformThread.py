# This file defines the main scientific functions behind transforming raw and .tif data
# into Q-Chi plots. Its main element is the class TransformThread, a thread that
# runs parallel to the GUI.
#
# This is one of the six main files (IntegrateThread, MONster, monster_queueloader, monster_transform, monster_stitch, TransformThread) that controls the MONster GUI. 
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
import glob, os, time, re, random, time, pyFAI
import numpy as np
import Properties
#####################################################################
#from monDimReduce import SAXSDimReduce all the things below are pertaining to this module
from os.path import basename
# import modules
#from input_file_parsing import parse_calib
from image_loader import load_image
from data_reduction_smooth import data_reduction
from saveDimRedPack import save_Qchi
from nearest_neighbor_cosine_distances import nearst_neighbor_distance
from PIL import Image
from scipy import signal
import shutil
###############################################################

# This class defines a detector data type
class Detector():
    def __init__(self, name, width, height):
        self.name = name
        self.width = width
        self.height = height
        
    def __eq__(self, other):
        return type(other) == Detector and self.name == other.name and self.width == other.width and self.height == other.height
    
    def __repr__(self):
        return ("%s: , Width: %s, Height: %s" % (self.name, self.width, self.height))
    
    def getName(self):
        return self.name
    
    def getWidth(self):
        return self.width
    
    def getHeight(self):
        return self.height
# This class defines the TransformThread, the main processing thread to create and save q-chi plots
# based on the tif and raw files the user supplies.
class TransformThread(QThread):

    def __init__(self, windowreference, processedPath, calibPath, detectorData, files_to_process):
        QThread.__init__(self)
        self.calibPath = calibPath
        self.processedPath = processedPath
        self.detectorData = detectorData
        self.abort_flag = False
        self.files_to_process = files_to_process
        self.windowreference = windowreference
        self.curDetector = None
        try:
            if os.path.isdir(files_to_process[0]):
                self.dataPath = files_to_process[0]
            else:   
                self.dataPath = os.path.dirname(files_to_process[0])
        except TypeError: # Nonetype error happens when initializing transform thread with Nones
            pass
        if detectorData is not None:
            detector = detectorData[6]
            if ":" in detector:
                detector = detector[:detector.index(":")]
            
            for detect in self.windowreference.detectorList:
                if detect.getName() == detector:
                    self.curDetector = detect
                    break
        
    def setAbortFlag(self, boo):
        self.abort_flag = boo
        
    def getDataPath(self):
        return self.dataPath
    
    def setDataPath(self, dataPath):
        self.dataPath = dataPath
        
    def getCalibPath(self):
        return self.calibPath
    
    def setCalibPath(self, calibPath):
        self.calibPath = calibPath      
    def getDetectorData(self):
        return self.detectorData
    
    def setDetectorData(self, detectorData):
        self.detectorData = detectorData
        
    def setFilesToProcess(self, files_to_process):
        self.files_to_process = files_to_process
        
    def stop(self):
        self.terminate()
    def __del__(self):
        self.wait()
        
    def abortClicked(self):
        self.emit(SIGNAL("enableWidgets()"))
        try:
            if self.isRunning():
                self.emit(SIGNAL("addToConsole(PyQt_PyObject)"), "Process aborted! Completing any processes that were already started...")                
                self.abort_flag = True
                QApplication.processEvents()
            else:
                self.emit(SIGNAL("addToConsole(PyQt_PyObject)"), "No process to abort!")
        except:
            self.emit(SIGNAL("addToConsole(PyQt_PyObject)"), "No process to abort!")
     
    # Begins the transformation, assuming that all the relevant calibration and data information
    # has been correctly passed into TransformThread's __init__
    def beginTransform(self):
        QApplication.processEvents()
        ##########################################Extension chooser?...
        if os.path.isdir(self.files_to_process[0]):
            fileList = sorted(glob.glob(os.path.join(self.dataPath, '*.tif')))
            if len(fileList) == 0:
                fileList = sorted(glob.glob(os.path.join(self.dataPath, '*.raw')))
                if len(fileList) == 0:
                    self.emit(SIGNAL("addToConsole(PyQt_PyObject)"), "No files found in specified source directory!")
                    self.emit(SIGNAL("enable()"))
                    return
           
            files = fileList[0:10000000000000000]
        else:
            files = [x for x in self.files_to_process if x.endswith('.raw') or x.endswith('.tif')]
        loopTime = []
        stage1Time = []
        stage2Time = []
        increment = (1/float(len(files)))*100
        progress = 0
        self.emit(SIGNAL("bar(int, PyQt_PyObject)"), 0, progress)
        self.emit(SIGNAL("resetTransform(PyQt_PyObject)"), self.windowreference) 
        self.emit(SIGNAL("addToConsole(PyQt_PyObject)"), "Using detector %s"% self.curDetector.getName())        
        save_path = str(self.processedPath)
        if os.path.exists(save_path):
            shutil.rmtree(save_path)    
        
        os.makedirs(save_path)
        for filePath in files:

            QApplication.processEvents()
            if (self.abort_flag):
                writeTransformProperties()
                self.emit(SIGNAL("enableWidgets()"))                
                break
            filename = os.path.basename(filePath)
        
               
            start = time.time()
            
            self.emit(SIGNAL("addToConsole(PyQt_PyObject)"), '{0}'.format(filePath))
            self.emit(SIGNAL("addToConsole(PyQt_PyObject)"), filename + ' detected, processing')
            
            QApplication.processEvents()
            ########## Begin data reduction scripts ###########################
            self.beginReduction(filePath) #QRange=QRange, ChiRange=ChiRange) # this is where the MAIN PROCESSING STUFF HAPPENS
            stage1int = time.time()
           
        
            
            QApplication.processEvents()
                       #peakFitBBA(filePath, config)
            stage2int = time.time()
            ########## Visualization #########################################
            # Pulling info from master CSV
            #FWHMmap(filePath)
            #contrastMap(filePath, hiLimit)
        
            self.emit(SIGNAL("addToConsole(PyQt_PyObject)"), filename + " completed")
            QApplication.processEvents()
            end = time.time()
            loopTime += [(end-start)]
            stage1Time += [(stage1int - start)]
            stage2Time += [(stage2int - stage1int)]
        
    
            save_path = os.path.join(os.path.dirname(filePath), "Processed_Transform")
            imageFilename = os.path.basename(filePath.rsplit('.', 1)[0])
            # Edit the "lastrun.txt" file so that if the program is stopped or aborted, next time the user launches MONster, the current information will be loaded
            with open("thisRun.txt", 'w') as runFile:
                
                runFile.write("t_data_source = \"" + str(self.dataPath)+'\"\n')
                runFile.write("t_calib_source = \"" + str(self.calibPath)+'\"\n')
                runFile.write("t_processed_loc = \"" + str(self.processedPath )+ '\"\n')
                name = os.path.join(save_path, os.path.splitext(imageFilename)[0]+'_gamma.png')                
                self.emit(SIGNAL("setRawImage(PyQt_PyObject)"), (name))
                runFile.write("two_d_image = \"" + name + '\"\n')
                     
                QApplication.processEvents()
                        
            progress += increment

            self.emit(SIGNAL("bar(int, PyQt_PyObject)"), 0, progress)
  
        writeTransformProperties()
        self.emit(SIGNAL("finished(PyQt_PyObject, PyQt_PyObject, PyQt_PyObject)"), loopTime, stage1Time, stage2Time)
        #self.stop()

    # Plots and displays the q-chi graph by using the calibration data to calculate the graph's shape
        
    def beginReduction(self, pathname):# Defines which lines are wanted/unwanted when writing previous run information during transforming

        '''
        Processing script, reducing images to 1D plots (Q-Chi, Texture, etc)
        '''
        print('\n')
        print('******************************************** Begin image reduction...')
        # PP: beam polarization, according to beamline setup. 
        # Contact beamline scientist for this number
        self.PP = 0.95   
        pixelSize = 79  # detector pixel size, measured in microns

        # pathname was imageFullName
        folder_path = os.path.dirname(pathname)
        filename = os.path.basename(pathname)
        # fileRoot was imageFilename
        fileRoot, ext = os.path.splitext(filename)
        index = re.match('.*?([0-9]+).[a-zA-Z]+$',filename).group(1)
        base_filename = re.match('(.*?)[0-9]+.[a-zA-Z]+$',filename).group(1) # name w/o ind

        # Master CSV path
        masterPath = os.path.join(folder_path,base_filename + 'master.csv')# Defines which lines are wanted/unwanted when writing previous run information during transforming


        # generate a folder to put processed files
        save_path = self.processedPath
       

        # make master index (vestigial)
        master_index = str(int(random.random()*100000000))

        attDict = dict.fromkeys(['scanNo', 'SNR', 'textureSum', 'Imax',
                                     'Iave', 'I_ratio', 'numPeaks'])
        #attribute1=[['scan#', 'Imax', 'Iave', 'Imax/Iave']]
        #attribute2=[['scan#', 'texture_sum']]
        #attribute3=[['scan#', 'peak_num']]
        #attribute4=[['scan#', 'neighbor_distance']]
        #attribute5=[['scan#', 'SNR']]

        ###### BEGIN READING CALIB FILE ################################################## Defines which lines are wanted/unwanted when writing previous run information during transforming

        # initializing params, transform the calibration parameters from WxDiff to Fit2D
        d_in_pixel = float(str(self.detectorData[0]))
        Rotation_angle = float(str(self.detectorData[1]))
        tilt_angle = float(str(self.detectorData[2]))
        lamda = float(str(self.detectorData[3]))
        x0 = float(str(self.detectorData[4]))
        y0 = float(str(self.detectorData[5]))
        #d_in_pixel, Rotation_angle, tilt_angle, lamda, x0, y0 = parse_calib(calibPath)
        Rot = (np.pi * 2 - Rotation_angle) / (2 * np.pi) * 360  # detector rotation
        tilt = tilt_angle / (2 * np.pi) * 360  # detector tilt  # wavelength
        d = d_in_pixel * pixelSize * 0.001  # measured in milimeters

        ###### BEGIN PROCESSING IMAGE####################################################
        # import image and convert it into an array
        self.imArray = load_image(pathname.rstrip(), self.curDetector)

        # data_reduction to generate Q-chi, Q
        Q, chi, cake, = self.data_reduction(d, Rot, tilt, lamda, x0, y0, pixelSize)


        ###### SAVE PLOTS ###############################################################
        # save Qchi as a plot *.png and *.mat
        qname = save_Qchi(Q, chi, cake, fileRoot, save_path)
    
    # Uses pyFAI to integrate the tif file as a one dimensional plot
        
    def data_reduction(self, d, Rot, tilt, lamda, x0, y0, pixelsize):
        """
        The input is the raw file's name and calibration parameters
        return Q-chi (2D array) 
        """    
        s1 = int(self.imArray.shape[0])
        s2 = int(self.imArray.shape[1])
        self.imArray = signal.medfilt(self.imArray, kernel_size = 5)
    
        detector_mask = np.ones((s1,s2))*(self.imArray <= 0)
        p = pyFAI.AzimuthalIntegrator(wavelength=lamda)
    
        # refer to http://pythonhosted.org/pyFAI/api/pyFAI.html for pyFAI parameters
        p.setFit2D(d,x0,y0,tilt,Rot,pixelsize,pixelsize) 
    
        # the output unit for Q is angstrom-1.  Always integrate all in 2D
        cake,Q,chi = p.integrate2d(self.imArray,1000, 1000,
                                   #azimuth_range=azRange, radial_range=radRange,
                                mask = detector_mask, polarization_factor = self.PP)
    
        # pyFAI output unit for Fit2D gemoetry incorrect. Multiply by 10e8 for correction
        Q = Q * 10e8  
    
  
        return Q, chi, cake
        
    def run(self):
        self.beginTransform()
        
# Writes the latest transform run info into the Properties.py file
def writeTransformProperties():
    prop = open("Properties.py", 'r')
    properties = []
    for line in prop:
        properties.append(line)
    prop.close()
    with open("thisRun.txt", 'r') as thisrun:
        properties[0] = thisrun.readline()
        properties[3] = thisrun.readline()
        properties[5] = thisrun.readline()
        properties[8] = thisrun.readline()
    propw = open("Properties.py", 'w')
    for prawperty in properties:
        propw.write(prawperty)
    propw.close()
        