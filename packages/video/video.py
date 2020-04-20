#!/usr/bin/python3
# -*- coding: utf-8 -*-

# http://www.mplayerhq.hu/DOCS/tech/slave.txt
# https://github.com/larsmagne/mplayer/blob/master/DOCS/tech/slave.txt

from TxtStyle import *
import sys, os

import subprocess

# The following should be taken from mplayers output when being
# invoked with -identify 
ID_VIDEO_WIDTH=384
ID_VIDEO_HEIGHT=288

ASPECT = ID_VIDEO_WIDTH/ID_VIDEO_HEIGHT

class MplayerWidget(QLabel):
    percent = pyqtSignal(int)
    paused = pyqtSignal(bool)
    
    def __init__(self, parent = None):
        QLabel.__init__(self, parent)
        self.setStyleSheet("background-color: black");
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(True)
        self.setSizePolicy(sizePolicy)
        self.values = { }
        self.m_paused = True
        self.ignoreOneSetPosition = False

    def sizeHint(self):
        return QSize(ID_VIDEO_WIDTH, ID_VIDEO_HEIGHT)
    
    def heightForWidth(self, width):
        return width / ASPECT

    def processOutput(self):
        stdout = bytes(self.process.readAllStandardOutput()).decode()
        for line in stdout.splitlines():
            # parse ID fields (we basically don't nee do that, but one
            # day we may need that information to scale the widget
            # properly
            if line.startswith("ID_") and len(line.split("=")) == 2:
                name, value = line.split("=")

                # split name into subcategories and create entry
                # e.g. ID_AUDIO_NCH becomes values["id"]["audio"]["nch"]
                obj = self.values
                for nidx in range(len(name.split("_"))):
                    np = name.split("_")[nidx].lower()
                    if len(name.split("_"))-1 == nidx:
                        obj[np] = value.strip()
                    else:
                        if not np in obj:
                            obj[np] = { }
                        obj = obj[np]

            # parse ANS(wer) fields like ANS_PERCENT_POSITION
            if line.startswith("ANS_") and len(line.split("=")) == 2:
                name, value = line.split("=")
                if name.lower() == "ans_percent_position":
                    self.percent.emit(int(value))
    
    def embed(self):
        self.process  = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.start(
            'mplayer',
            [
                '-wid', str(self.winId()),
                "-slave", "-idle", "-quiet",
                "-identify", "-zoom", "-loop", "-1"
            ],
            QIODevice.ReadWrite)

        self.process.readyReadStandardOutput.connect(self.processOutput)
        self.process.readyReadStandardError.connect(self.processOutput)

        self.timer = QTimer()
        self.timer.timeout.connect(self.onTimer)
        self.timer.start(100)

    def startStop(self):
        if not self.m_paused:
            self.process.write("osd_show_text PAUSED\n")
            
        self.process.write("pause\n")        
        self.pause(not self.m_paused)

    def pause(self, paused):
        if paused != self.m_paused:
            self.paused.emit(paused)
            self.m_paused = paused
        
    def load(self, file):
        path = os.path.dirname(os.path.realpath(__file__))
        movie = os.path.join(path, file)
        self.process.write("loadfile "+movie+"\n")
        self.pause(False)
        
    def displayOSD(self, str):
        self.pause(False)
        self.process.write("osd_show_text "+str+"\n")
        
    def onTimer(self):
        # requesting the position while playing makes the video stutter
        if not self.m_paused:
            self.process.write("get_percent_pos\n")

    def backward(self):
        self.pause(False)
        self.process.write("seek -10\n")
        
    def forward(self):
        self.pause(False)
        self.process.write("seek 10\n")        
            
    def setPosition(self, percent):
        self.pause(False)
        self.process.write("seek "+str(percent)+ " 1\n")

class SeekSlider(QSlider):
    valueChangedInteractive = pyqtSignal(int)
    
    def __init__(self, parent):
        QSlider.__init__(self, Qt.Horizontal, parent)
        self.setRange(0, 100)
        self.valueChanged.connect(self.onValueChanged)
        self.externally_set = None

    def onValueChanged(self, value):
        if value != self.externally_set:
            self.valueChangedInteractive.emit(value)        

    def setValue(self, value):
        self.externally_set = value
        super().setValue(value)
        
class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)
        # create the empty main window
        self.w = TxtWindow("Video")

        self.video = MplayerWidget(self.w)
        self.vbox = QVBoxLayout()
        self.vbox.addStretch()
        self.vbox.addWidget(self.video)

        # create slider and connect slider with video widget
        self.slider = SeekSlider(self.w)
        self.video.percent.connect(self.slider.setValue)
        self.video.paused.connect(self.onPause)
        self.slider.valueChangedInteractive.connect(self.video.setPosition)
        self.vbox.addWidget(self.slider)

        # create hbox with control buttons
        hboxw = QWidget()
        hbox = QHBoxLayout()

        self.backwardBut = QPushButton("<<")
        self.backwardBut.clicked.connect(self.video.backward)
        hbox.addWidget(self.backwardBut)
        self.playBut = QPushButton()
        self.playBut.clicked.connect(self.video.startStop)
        hbox.addWidget(self.playBut)
        self.forwardBut = QPushButton(">>")
        self.forwardBut.clicked.connect(self.video.forward)
        hbox.addWidget(self.forwardBut)
        
        hboxw.setLayout(hbox)        
        self.vbox.addWidget(hboxw)
        
        self.vbox.addStretch()
        self.w.centralWidget.setLayout(self.vbox)
        
        # this must happen after the video widget has been placed
        # since the window id will change on placement
        self.video.embed()

        self.video.load('big_buck_bunny_480p_surround-fix.m4v')

        self.w.show()
        self.exec_()

    def onPause(self, paused):
        if not paused:
            self.playBut.setText("||")
        else:
            self.playBut.setText(">")
        
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)
