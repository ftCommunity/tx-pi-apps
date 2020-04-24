#!/usr/bin/env python3
#-*- coding:utf-8 -*-

from TxtStyle import *
import sys

class ShellWidget(QLabel):
    def __init__(self, parent = None):
        QLabel.__init__(self, parent)
        self.setStyleSheet("background-color: black");
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setSizePolicy(sizePolicy)

    def embed(self):
        self.process = QProcess(self)
        self.process.start(
            'xterm',
            ['-into', str(self.winId()),
             "-geometry", "100x50" ]
        )
        
class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)
        # create the empty main window
        self.w = TxtWindow("Shell")

        self.terminal = ShellWidget(self.w)
        self.w.setCentralWidget(self.terminal)
        self.w.show()

        self.terminal.embed()
        
        self.exec_()
        
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)

