# -*- coding: utf-8 -*-
"""
Program name: OpenWave-1KB

Copyright:
----------------------------------------------------------------------
OpenWave-1KB is Copyright (c) 2015 Good Will Instrument Co., Ltd All Rights Reserved.

This program is free software; you can redistribute it and/or modify it under the terms
of the GNU Lesser General Public License as published by the Free Software Foundation;
either version 2.1 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You can receive a copy of the GNU Lesser General Public License from http://www.gnu.org/

Note:
OpenWave-1KB uses third party software which is copyrighted by its respective copyright
holder. For details see the copyright notice of the individual package.

The Qt GUI Toolkit is Copyright (c) 2014 Digia Plc and/or its subsidiary(-ies).
OpenWave-1KB use Qt version 4.8 library under the terms of the LGPL version 2.1.
----------------------------------------------------------------------
Description:
OpenWave-1KB is a python example program used to get waveform and image from DSO.

Version: 1.02

Created on JUL 12 2018
Python3 3.7+ version compatible

Author: Kevin Meng, (2018)
Author: Marian Minar (2021)
"""
import matplotlib as mpl
mpl.use("Qt5Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from mpl_toolkits.axes_grid1 import host_subplot
import mpl_toolkits.axisartist as AA

from PyQt5.QtWidgets import * 
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import * 
from PyQt5.QtCore import * 
import sys

import numpy as np
from PIL import Image
import os, sys, time
from gw_com_1kb import com
from gw_lan import lan
import dso1kb
import re

__version__ = "1.03" #OpenWave-1KB software version.

def checkInterface(str):
    if str!= '':
        print (str)
    #Load config file if it exists
    elif os.path.exists('port.config'):
        f = open('port.config', 'r')
        while(1):
            str = f.readline()
            if(str == ''):
                f.close()
                return ''
            if(str[0] != '#'):
                break
        f.close()

    #Check ethernet connection(model name not checked)
    sInterface=str.split('\n')[0]
    #print 'sInterface=',sInterface
    if(sInterface.count('.') == 3 and sInterface.count(':') == 1): #Got ip address.
        ip_str=sInterface.split(':')
        ip=ip_str[0].split('.')
        if(ip_str[1].isdigit() and ip[0].isdigit() and ip[1].isdigit() and ip[2].isdigit() and ip[3].isdigit()):
            #print('ip addr=%s.%s.%s.%s:%s'%(ip[0],ip[1],ip[2],ip[3],ip_str[1]))
            str=lan.connection_test(sInterface)
            if(str != ''):
                return str
    #Check COM port connection(model name not checked)
    elif('COM' in sInterface):
        if(com.connection_test(sInterface) != ''):
            return sInterface
    elif('ttyACM' in sInterface):
        if 'ttyACM' == sInterface[0:6]:
            sInterface='/dev/'+sInterface
        if(com.connection_test(sInterface) != ''):
            return sInterface

    return com.scanComPort()  #Scan all the USB port.

class Window(QWidget):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.setWindowTitle('OpenWave-1KB V%s'%__version__)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("openwave.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)

        #Waveform area.
        self.figure = plt.figure()
        self.figure.set_facecolor('white')

        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(800,  400)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.hide()

        #Zoom In/out and Capture Buttons
        self.zoomBtn = QPushButton('Zoom')
        self.zoomBtn.setFixedSize(100, 30)
        self.zoomBtn.clicked.connect(self.toolbar.zoom)

        self.panBtn = QPushButton('Pan')
        self.panBtn.setFixedSize(100, 30)
        self.panBtn.clicked.connect(self.toolbar.pan)

        self.homeBtn = QPushButton('Home')
        self.homeBtn.setFixedSize(100, 30)
        self.homeBtn.clicked.connect(self.toolbar.home)

        self.captureBtn = QPushButton('Capture')
        self.captureBtn.setFixedSize(100, 50)
        self.captureBtn.clicked.connect(self.captureAction)
        if(dso.connection_status==0):
            self.captureBtn.setEnabled(False)

        # Continuous capture
        self.contBtn = QPushButton('Cont')
        self.contBtn.setToolTip("Toggle continuous mode.")
        self.contBtn.setFixedSize(100, 50)
        self.contFlag=False #Initial state -> do not capture continuosly
        self.contBtn.setCheckable(True)
        self.contBtn.setChecked(False)
        self.contBtn.clicked.connect(self.contAction)
        self.contTimer=QtCore.QTimer(self)
        self.contTimer.timeout.connect(self.captureAction)
        #self.contTimer.timeout.connect(self.handleCapture)
        
        # Continuous capture2
        self.contBtn2 = QPushButton('Cont2')
        self.contBtn2.setToolTip("Toggle continuous mode.")
        self.contBtn2.setFixedSize(100, 50)
        self.contFlag=False #Initial state -> do not capture continuosly
        self.contBtn2.setCheckable(True)
        self.contBtn2.setChecked(False)
        self.contBtn2.clicked.connect(self.contAction2)
        self.contTimer2=QtCore.QTimer(self)
        self.contTimer2.timeout.connect(self.captureAction)

        #Type: Raw Data/Image
        self.typeBtn = QPushButton('Raw Data')
        self.typeBtn.setToolTip("Switch to get raw data or image from DSO.")
        self.typeBtn.setFixedSize(120, 50)
        self.typeFlag=True #Initial state -> Get raw data
        self.typeBtn.setCheckable(True)
        self.typeBtn.setChecked(True)
        self.typeBtn.clicked.connect(self.typeAction)

        #Channel Selection.
        self.ch1checkBox = QCheckBox('CH1', self)
        self.ch1checkBox.setFixedSize(60, 30)
        self.ch1checkBox.setEnabled(True)
        if(dso.isChannelOn(1)):
            self.ch1checkBox.setChecked(True)
        self.ch2checkBox = QCheckBox('CH2', self)
        self.ch2checkBox.setFixedSize(60, 30)
        if(dso.isChannelOn(2)):
            self.ch2checkBox.setChecked(True)
        if(dso.chnum==4):
            self.ch3checkBox = QCheckBox('CH3', self)
            self.ch3checkBox.setFixedSize(60, 30)
            if(dso.isChannelOn(3)):
                self.ch3checkBox.setChecked(True)
            self.ch4checkBox = QCheckBox('CH4', self)
            self.ch4checkBox.setFixedSize(60, 30)
            if(dso.isChannelOn(4)):
                self.ch4checkBox.setChecked(True)

        #Set channel selection layout.
        self.selectLayout = QHBoxLayout()
        self.selectLayout.addWidget(self.ch1checkBox)
        self.selectLayout.addWidget(self.ch2checkBox)
        if(dso.chnum==4):
            self.selectLayout2 = QHBoxLayout()
            self.selectLayout2.addWidget(self.ch3checkBox)
            self.selectLayout2.addWidget(self.ch4checkBox)

        self.typeLayout = QHBoxLayout()
        self.typeLayout.addWidget(self.typeBtn)
        self.typeLayout.addLayout(self.selectLayout)
        if(dso.chnum==4):
            self.typeLayout.addLayout(self.selectLayout2)

        #Save/Load/Quit button
        self.saveBtn = QPushButton('Save')
        self.saveBtn.setFixedSize(100, 50)
        self.saveMenu = QMenu(self)
        self.csvAction = self.saveMenu.addAction("&As CSV File",self.SaveActionClicked)
        self.pictAction = self.saveMenu.addAction("&As PNG File",self.SaveActionClicked)
        self.saveBtn.setMenu(self.saveMenu)
        self.saveBtn.setToolTip("Save waveform to CSV file or PNG file.")
        
        #record button
        self.recordBtn = QPushButton('Record')
        self.recordBtn.setFixedSize(100, 50)
        self.recordBtn.clicked.connect(self.recordCsvAction)
        self.recordBtn.setToolTip("Record multiple frames of waveform to many CSV files.")

        self.loadBtn = QPushButton('Load')
        self.loadBtn.setToolTip("Load CHx's raw data from file(*.csv, *.lsf).")
        self.loadBtn.setFixedSize(100, 50)
        self.loadBtn.clicked.connect(self.loadAction)

        self.quitBtn = QPushButton('Quit')
        self.quitBtn.setFixedSize(100, 50)
        self.quitBtn.clicked.connect(self.quitAction)

        # set the layout
        self.defaultLengthOfCapture = "10"
        self.recordLayout = QVBoxLayout()
        self.recordLayout.addWidget(QLabel("No. of Frames"))
        self.framesLineEdit = QLineEdit()
        self.framesLineEdit.setPlaceholderText(self.defaultLengthOfCapture)
        self.framesLineEdit.setMaximumWidth(100)
        self.recordLayout.addWidget(self.framesLineEdit)
        self.recordLayout.addWidget(self.recordBtn)

        self.waveLayout = QHBoxLayout()
        self.waveLayout.addWidget(self.canvas)

        self.wave_box=QVBoxLayout()
        self.wave_box.addLayout(self.waveLayout)

        self.wavectrlLayout = QHBoxLayout()
        self.wavectrlLayout.addWidget(self.zoomBtn)
        self.wavectrlLayout.addWidget(self.panBtn)
        self.wavectrlLayout.addWidget(self.homeBtn)
        self.wavectrlLayout.addWidget(self.captureBtn)
        self.wavectrlLayout.addWidget(self.contBtn)
        self.wavectrlLayout.addLayout(self.recordLayout)

        self.saveloadLayout = QHBoxLayout()
        self.saveloadLayout.addWidget(self.saveBtn)
        self.saveloadLayout.addWidget(self.loadBtn)
        self.saveloadLayout.addWidget(self.quitBtn)

        self.ctrl_box=QHBoxLayout()
        self.ctrl_box.addLayout(self.typeLayout)
        self.ctrl_box.addLayout(self.saveloadLayout)

        main_box=QVBoxLayout()
        main_box.addLayout(self.wave_box)         #Waveform area.
        main_box.addLayout(self.wavectrlLayout)   #Zoom In/Out...
        main_box.addLayout(self.ctrl_box)         #Save/Load/Quit
        self.setLayout(main_box)
        
    def SaveActionClicked(self):
        action = self.sender()
        if (action.text() == '&As PNG File') :
            self.savePngAction()
        elif (action.text() == '&As CSV File') :
            self.saveCsvAction()

    def typeAction(self):
        if(self.typeFlag==True):
            self.typeFlag=False
            self.typeBtn.setText("Image")
            self.csvAction.setEnabled(False)
        else:
            self.typeFlag=True
            self.typeBtn.setText("Raw Data")
            self.csvAction.setEnabled(True)
        self.typeBtn.setChecked(self.typeFlag)
        #self.ch1checkBox.setEnabled(self.typeFlag)
        self.ch2checkBox.setEnabled(self.typeFlag)
        if(dso.chnum==4):
            self.ch3checkBox.setEnabled(self.typeFlag)
            self.ch4checkBox.setEnabled(self.typeFlag)
    def recordCsvAction(self):
        if(self.typeFlag==True): #Save raw data to csv file.
            file_name=QFileDialog.getSaveFileName(self, "Save as", 'temp', "Fast CSV File(*.CSV)")[0]
            if re.search(r'\.\w{3}$',file_name) == None : 
                file_name = file_name
            elif(file_name==''):
                return
            numCaptures = int(self.defaultLengthOfCapture)
            try:
                numCaptures = int(self.framesLineEdit.text())
            except ValueError :
                print(f"error in value, proceeding with default {self.defaultLengthOfCapture} captures")
                numCaptures = int(self.defaultLengthOfCapture)
            assert numCaptures>0
            for file_index in range(numCaptures):
                if file_index %100==0:
                    if file_index %500==0:
                        print(file_index, "marker")
                    else:
                        print(file_index)
                self.captureAction_FetchData()
                self.save_file(file_name[:-4]+f"{file_index:07d}"+".CSV")
            print("done long capture")
    def saveCsvAction(self):
        if(self.typeFlag==True): #Save raw data to csv file.
            file_name=QFileDialog.getSaveFileName(self, "Save as", '', "Fast CSV File(*.CSV)")[0]
            if re.search(r'\.\w{3}$',file_name) == None : 
                file_name = file_name + '.csv'
            elif(file_name==''):
                return
            self.save_file(file_name)
            
    def save_file(self,file_name):
            num=len(dso.ch_list)
            #print num
            for ch in range(num):
                if(dso.info[ch]==[]):
                    print('Failed to save data, raw data information is required!')
                    return
            f = open(file_name, 'w+')
            item=len(dso.info[0])
            #Write file header.
            if any(dso.osname == a for a in ['win','win10']) : 
                f.write('%s,\n' % dso.info[0][0])
            else :
                f.write('%s,\r\n' % dso.info[0][0])
            for x in range(1,  23):
                str=''
                for ch in range(num):
                    str+=('%s,' % dso.info[ch][x])
                if any(dso.osname == a for a in ['win','win10']) : 
                    str+='\n'
                else :
                    str+='\r\n'
                f.write(str)
            #Write Fast CSV mode only.
            str=''
            for ch in range(num):
                str+='Mode,Fast,'
            if any(dso.osname == a for a in ['win','win10']) : 
                str+='\n'
            else :
                str+='\r\n'
            f.write(str)

            str=''
            if(num==1):
                str+=('%s,' % dso.info[0][24])
            else:
                for ch in range(num):
                    str+=('%s,,' % dso.info[ch][24])
            if any(dso.osname == a for a in ['win','win10']) : 
                str+='\n'
            else :
                str+='\r\n'
            f.write(str)
            #Write raw data.
            item=len(dso.iWave[0])
            #print item
            tenth=int(item/10)
            n_tenth=tenth-1
            percent=10
            for x in range(item):
                str=''
                if(num==1):
                    str+=('%s,' % dso.iWave[0][x])
                else:
                    for ch in range(num):
                        str+=('%s, ,' % dso.iWave[ch][x])
                if any(dso.osname == a for a in ['win','win10']) : 
                    str+='\n'
                else :
                    str+='\r\n'
                f.write(str)
                if(x==n_tenth):
                    n_tenth+=tenth
                    # print('%3d %% Saved\r'%percent),
                    percent+=10
            #print('%3d %% Saved\r'%percent)
            f.close()
    def savePngAction(self):
        #Save figure to png file.
        file_name=QFileDialog.getSaveFileName(self, "Save as", '', "PNG File(*.png)")[0]
        if re.search(r'\.\w{3}$',file_name) == None : 
                file_name = file_name + '.png'
        elif(file_name==''):
            return
        if(self.typeFlag==True): #Save raw data waveform as png file.
            main.figure.savefig(file_name)
        else:  #Save figure to png file.
            model_name = dso.model_name
            if(dso.osname=='pi') and any(model_name == a for a in dso.sModelTranspose) : #For raspberry pi only.
                img=dso.im.transpose(Image.FLIP_TOP_BOTTOM)
                img.save(file_name)
            else:
                dso.im.save(file_name)
        print('Saved image to %s.'%file_name)

    def loadAction(self):
        dso.ch_list=[]
        full_path_name=QFileDialog.getOpenFileName(self,self.tr("Open File"),".","CSV/LSF files (*.csv *.lsf);;All files (*.*)")
        p=re.compile('^\(\'(.*)\'\,')
        m=p.match(str(full_path_name))
        sFileName=m.group(1)
        if(len(sFileName)<=0):
            return
        if os.path.exists(sFileName):
            print ('Reading file...')
            count=dso.readRawDataFile(sFileName)
            #Draw waveform.
            if(count>0):
                total_chnum=len(dso.ch_list)
                if(total_chnum==0):
                    return
                self.drawWaveform(0)
        else:
            print('File not found!')

    def quitAction(self):
        if(dso.connection_status==1):
            dso.closeIO()
        self.close()
        
    def contAction(self):
        print("contAction")
        if(self.contFlag==True):
            self.contFlag=False
        else:
            self.contFlag=True
        self.contBtn.setChecked(self.contFlag)
        if self.contFlag:
            self.contTimer.start(5) # sample every xxx milliseconds
        else:
            self.contTimer.stop()
    def contAction2(self):
        print("contAction2")
        if(self.contFlag==True):
            self.contFlag=False
        else:
            self.contFlag=True
        self.contBtn2.setChecked(self.contFlag)
        if self.contFlag:
            self.contTimer.start(5) # sample every xxx milliseconds
        else:
            self.contTimer.stop()
    def captureAction_FetchData(self):
        dso.iWave=[[], [], [], []]
        dso.ch_list=[]
        if(self.typeFlag==True): #Get raw data.
            draw_flag=False
            #Turn on the selected channels.
            if((self.ch1checkBox.isChecked()==True) and (dso.isChannelOn(1)==False)):
                dso.write(":CHAN1:DISP ON\n")           #Set CH1 on.
            if((self.ch2checkBox.isChecked()==True) and (dso.isChannelOn(2)==False)):
                dso.write(":CHAN2:DISP ON\n")           #Set CH2 on.
            if(dso.chnum==4):
                if((self.ch3checkBox.isChecked()==True) and (dso.isChannelOn(3)==False)):
                    dso.write(":CHAN3:DISP ON\n")       #Set CH3 on.
                if((self.ch4checkBox.isChecked()==True) and (dso.isChannelOn(4)==False)):
                    dso.write(":CHAN4:DISP ON\n")       #Set CH4 on.
            #Get all the selected channel's raw datas.
            if(self.ch1checkBox.isChecked()==True):
                dso.getRawData(True, 1)              #Read CH1's raw data from DSO (including header).
            if(self.ch2checkBox.isChecked()==True):
                dso.getRawData(True, 2)              #Read CH2's raw data from DSO (including header).
            if(dso.chnum==4):
                if(self.ch3checkBox.isChecked()==True):
                    dso.getRawData(True, 3)          #Read CH3's raw data from DSO (including header).
                if(self.ch4checkBox.isChecked()==True):
                    dso.getRawData(True, 4)          #Read CH4's raw data from DSO (including header).
    def captureAction(self):
        dso.iWave=[[], [], [], []]
        dso.ch_list=[]
        if(self.typeFlag==True): #Get raw data.
            draw_flag=False
            #Turn on the selected channels.
            if((self.ch1checkBox.isChecked()==True) and (dso.isChannelOn(1)==False)):
                dso.write(":CHAN1:DISP ON\n")           #Set CH1 on.
            if((self.ch2checkBox.isChecked()==True) and (dso.isChannelOn(2)==False)):
                dso.write(":CHAN2:DISP ON\n")           #Set CH2 on.
            if(dso.chnum==4):
                if((self.ch3checkBox.isChecked()==True) and (dso.isChannelOn(3)==False)):
                    dso.write(":CHAN3:DISP ON\n")       #Set CH3 on.
                if((self.ch4checkBox.isChecked()==True) and (dso.isChannelOn(4)==False)):
                    dso.write(":CHAN4:DISP ON\n")       #Set CH4 on.
            #Get all the selected channel's raw datas.
            if(self.ch1checkBox.isChecked()==True):
                dso.getRawData(True, 1)              #Read CH1's raw data from DSO (including header).
            if(self.ch2checkBox.isChecked()==True):
                dso.getRawData(True, 2)              #Read CH2's raw data from DSO (including header).
            if(dso.chnum==4):
                if(self.ch3checkBox.isChecked()==True):
                    dso.getRawData(True, 3)          #Read CH3's raw data from DSO (including header).
                if(self.ch4checkBox.isChecked()==True):
                    dso.getRawData(True, 4)          #Read CH4's raw data from DSO (including header).
            #Draw waveform.
            total_chnum=len(dso.ch_list)
            if(total_chnum==0):
                return
            if(self.drawWaveform(1)==-1):
                time.sleep(5)
                self.drawWaveform(0)
        else: #Get image.
            img_type=1   #1 for RLE format, 0 for PNG format.
            if(img_type):
                dso.write(':DISP:OUTP?\n')                 #Send command to get image from DSO.
            else:
                dso.write(':DISP:PNGOutput?\n')            #Send command to get image from DSO.
            dso.getBlockData()
            dso.ImageDecode(img_type)
            self.showImage()
            self.canvas.draw()
            print('Image is ready!')

    def showImage(self):
        #Turn the ticks off and show image.
        plt.clf()
        ax = plt.gca()
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        plt.imshow(dso.im)

    def drawWaveform(self, mode):
        total_chnum=len(dso.ch_list)
        num=dso.points_num
        ch_colortable=['#C0B020',  '#0060FF',  '#FF0080',  '#00FF60']
        ch=int(dso.ch_list[0][2])-1 #Get the channel of first waveform.
        plt.cla()
        plt.clf()
        #Due to the memory limitation of matplotlib, we must reduce the sample points.
        if(num==10000000):
            if(total_chnum>2):
                down_sample_factor=4
            elif(total_chnum==2):
                down_sample_factor=4
            else:
                down_sample_factor=1
            num=num/down_sample_factor
        else:
            down_sample_factor=1
        dt=dso.dt[0] #Get dt from the first opened channel.
        t_start=dso.hpos[0]-num*dt/2
        t_end  =dso.hpos[0]+num*dt/2
        t = np.arange(t_start, t_end, dt)
        #print t_start, t_end, dt, len(t)
        if((len(t)-num)==1): #Avoid floating point rounding error.
            t=t[:-1]
        wave_type='-' #Set waveform type to vector.
        #Draw waveforms.
        ax=[[], [], [], []]
        p=[]
        for ch in range(total_chnum):
            if(ch==0):
                ax[ch]=host_subplot(111, axes_class=AA.Axes)
                ax[ch].set_xlabel("Time (sec)")
            else:
                ax[ch]=ax[0].twinx()
            ax[ch].set_ylabel("%s Units: %s" %(dso.ch_list[ch],  dso.vunit[ch]))
            ch_color=ch_colortable[int(dso.ch_list[ch][2])-1]
            if(ch>1):
                new_fixed_axis = ax[ch].get_grid_helper().new_fixed_axis
                ax[ch].axis["right"] = new_fixed_axis(loc="right", axes=ax[ch], offset=(60*(ch-1), 0))
            ax[ch].set_xlim(t_start, t_end)
            ax[ch].set_ylim(-4*dso.vdiv[ch]-dso.vpos[ch], 4*dso.vdiv[ch]-dso.vpos[ch]) #Setup vertical display range.
            fwave=dso.convertWaveform(ch, down_sample_factor)
            #print('Length=%d'%(len(fwave)))
            if(ch==0):
                try:
                    p=ax[ch].plot(t, fwave, color=ch_color, ls=wave_type, label = dso.ch_list[ch])
                except:
                    if(mode==1):
                        #print sys.exc_info()[0]
                        time.sleep(5)
                        print ('Trying to plot again!')
                    return -1
            else:
                try:
                    p+=ax[ch].plot(t, fwave, color=ch_color, ls=wave_type, label = dso.ch_list[ch])
                except:
                    if(mode==1):
                        #print sys.exc_info()[0]
                        time.sleep(5)
                        print ('Trying to plot again!')
                    return -1
        if(total_chnum>1):
            labs = [l.get_label() for l in p]
            plt.legend(p, labs,   loc='upper right')
        plt.tight_layout()
        self.canvas.draw()
        del ax, t, p
        return 0

if __name__ == '__main__':

    f = open('license.txt', 'r')
    print('-----------------------------------------------------------------------------');
    print (f.read())
    f.close()
    print('-----------------------------------------------------------------------------');
    print('OpenWave-1KB V%s\n'% __version__)

    #Get command line arguments.
    cmd=sys.argv[-1]
    if('OpenWave' in cmd):
        cmd=''

    #Check interface according to config file or command line argument.
    port=checkInterface(cmd)

    #Connecting to a DSO.
    dso=dso1kb.Dso(port)

    app = QApplication(sys.argv)

    main = Window()

    main.show()

    sys.exit(app.exec_())
