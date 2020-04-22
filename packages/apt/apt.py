#!/usr/bin/env python3
#-*- coding:utf-8 -*-

from TxtStyle import *
import sys, bisect

# ../../user/video/video.py

# a rotating "i am busy" widget to be shown during network io
class BusyAnimation(QWidget):
    expired = pyqtSignal()

    def __init__(self, parent=None):
        super(BusyAnimation, self).__init__(parent)

        self.resize(64, 64)
        self.move(QPoint(parent.width()/2-32, parent.height()/2-32))

        self.step = 0
        self.percent = None

        # animate at 5 frames/sec
        self.atimer = QTimer(self)
        self.atimer.timeout.connect(self.animate)
        self.atimer.start(200)

        # create small circle bitmaps for animation
        self.dark = self.draw(16, QColor("#808080"))
        self.bright = self.draw(16, QColor("#fcce04"))
        
    def progress(self, perc):
        self.percent = perc
        self.repaint()
    
    def draw(self, size, color):
        img = QImage(size, size, QImage.Format_ARGB32)
        img.fill(Qt.transparent)

        painter = QPainter(img)
        painter.setPen(Qt.white)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(0, 0, img.width()-1, img.height()-1)
        painter.end()

        return img

    def animate(self):
        self.step += 45
        self.repaint()

    def close(self):
        self.atimer.stop()
        super(BusyAnimation, self).close()

    def paintEvent(self, event):
        self.move(QPoint(self.parent().width()/2-32, self.parent().height()/2-32))
        
        radius = min(self.width(), self.height())/2 - 16
        painter = QPainter()
        painter.begin(self)

        if self.percent != None:
            font = painter.font()
            # half the size than the current font size 
            if font.pointSize() < 0:
                font.setPixelSize(font.pixelSize() / 3)
            else:
                font.setPointSize(font.pointSize() / 3)
            # set the modified font to the painter */
            painter.setFont(font)

            # draw text in center
            painter.drawText(QRect(0, 0, self.width(), self.height()), Qt.AlignCenter, str(self.percent)+"%" )

        painter.setRenderHint(QPainter.Antialiasing)

        painter.translate(self.width()/2, self.height()/2)
        painter.rotate(45)
        painter.rotate(self.step)
        painter.drawImage(0,radius, self.bright)
        for i in range(7):
            painter.rotate(45)
            painter.drawImage(0,radius, self.dark)

        painter.end()

class PacketListView(QListView):
    select = pyqtSignal(str)
    
    style = ( "font-size: 20px;"
              "background: #5c96cc;"
              "alternate-background-color: rgba(0,0,0,16);"
    )
        
    def __init__(self, parent):
        super(PacketListView, self).__init__(parent)
        # self.model = QStringListModel()
        self.model = QStandardItemModel()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setModel(self.model)
        self.setStyleSheet(self.style)
        self.setAlternatingRowColors(True)
        self.setUniformItemSizes(True)            
        self.setLayoutMode( QListWidget.Batched );
        self.setBatchSize( 10 );
        self.clicked.connect(self.onClick)       

    def setPacketList(self, names, installed):
        icon = QIcon(os.path.join(os.path.dirname(os.path.realpath(__file__)), "installed.png"))
        pix = QPixmap(16, 16)
        pix.fill(QColor("black"));
        pix.setAlphaChannel(pix);
        noicn = QIcon(pix)

        for n in names:
            # use bisect on the sorted list since a regular "in" operation
            # would be way too slow
            index = bisect.bisect_left(installed, n)
            if index > len(installed)-1 or installed[index] != n:            
                self.model.appendRow(QStandardItem(noicn, n))
            else:
                self.model.appendRow(QStandardItem(icon, n))
                
        # with QStringListModel:
        # self.model.setStringList(names)
            
    def onClick(self, index):
        print("CLICK:", self.model.data(index,0))
        self.select.emit(self.model.data(index,0))
        
class SearchWidget(QWidget):
    request = pyqtSignal(str)
    select = pyqtSignal(str)

    def __init__(self, parent=None):
        super(SearchWidget, self).__init__(parent)

        # a vertical box 
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        vbox.setContentsMargins(0,0,0,0)

        searchBox = QWidget()
        hbox = QHBoxLayout()
        searchBox.setLayout(hbox)
        hbox.setContentsMargins(0,0,0,0)

        self.lineEdit = QLineEdit(self)
        hbox.addWidget(self.lineEdit)
        searchBut = QPushButton("Go", self)
        searchBut.clicked.connect(self.doSearch)
        hbox.addWidget(searchBut)

        vbox.addWidget(searchBox)
        self.searchResults = PacketListView(self)
        self.searchResults.select.connect(self.onSelect)
        vbox.addWidget(self.searchResults)

    def onSelect(self, pkgname):
        self.select.emit(pkgname)
        
    def doSearch(self):
        self.request.emit(self.lineEdit.text())

    def setResult(self, packages, installed):
        # print("Result:", result)
        self.searchResults.setPacketList(packages, installed)

class AppDialog(TouchDialog):
    def __init__(self, package, parent):
        TouchDialog.__init__(self, package["Package"], parent)
        text = QTextEdit()
        text.setReadOnly(True)
        for i in package:
            text.append('<h3><font color="#fcce04">'+i+'</font></h3>'+package[i]+"\n")
        text.moveCursor(QTextCursor.Start)
        self.setCentralWidget(text)

class AptWidget(QWidget):
    APT_CACHE = "/usr/bin/apt-cache"
    APT_GET = "/usr/bin/apt-get"
    DPKG = "/usr/bin/dpkg"

    def onCommand(self, cmd):
        print("cmd", cmd);
        if cmd == "List all":
            self.setContentPacketList(self)
            self.apt_cache_cmd(['pkgnames'])
        elif cmd == "Search":
            self.setContentSearch(self)
        else:            
            self.setContentString(cmd, self)

    def removeOldContent(self):
        if self.content != None:
            self.content.deleteLater()
            self.vbox.removeWidget(self.content)
            self.content = None
        
    def setContentPacketList(self, parent):
        self.removeOldContent()
        self.list = PacketListView(parent)
        self.list.select.connect(self.showPackage)
        self.vbox.addWidget(self.list)        
        self.content = self.list
        
    def setContentSearch(self, parent):
        self.removeOldContent()

        self.search = SearchWidget()
        self.search.request.connect(self.doSearch)
        self.search.select.connect(self.showPackage)
        self.vbox.addWidget(self.search)        
        self.content = self.search

    def showPackage(self, pkgname):
        print("Search Details for", pkgname)
        self.apt_cache_cmd(["show", pkgname])
        
    def doSearch(self, str):
        print("search: ", str)
        self.apt_cache_cmd(["search", str ] )
        
    def setContentString(self, str, parent):
        self.removeOldContent()        
        self.label = QLabel(str, parent)
        self.vbox.addWidget(self.label)
        self.content = self.label
        
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setSizePolicy(sizePolicy)
        self.vbox = QVBoxLayout()
        self.vbox.setContentsMargins(0,0,0,0)
        self.vbox.setSpacing(0)

        # add command combobox
        self.combo = QComboBox(self)
        self.combo.addItem("List all")
        self.combo.addItem("Search")
        self.combo.addItem("Update")
        self.combo.activated[str].connect(self.onCommand)
        self.combo.setCurrentIndex(-1)
        self.vbox.addWidget(self.combo)
        
        # add empty content widget
        self.content = QWidget()
        self.vbox.addWidget(self.content)        

        self.setLayout(self.vbox)        
        self.busy = None

        # immediately scan for installed apps
        self.dpkg_cmd(["-l"])
        
    def processError(self):
        pass
        
    def processOutput(self):
        results = bytes(self.process.readAllStandardOutput()).decode()
        self.results = self.results + results

    def showPackageDialog(self, package):
        dialog = AppDialog(package, self)
        dialog.exec_()

    def parseShowResults(self, str):
        def htmlize(str):
            str = str.replace("&", "&amp;")
            str = str.replace("<", "&lt;")
            str = str.replace(">", "&gt;")
            return str
        
        # split into lines and process line by line
        results = { }
        name = None
        for line in str.split("\n"):
            # ignore empty lines
            if len(line) > 0:
                if not line.startswith(" "):
                    # we expect at least one ':' in each line
                    if len(line.split(":")) > 1:
                        name = line.split(":")[0].strip()
                        value = ":".join(line.split(":")[1:]).strip()
                        results[name] = htmlize(value)
                else:
                    # lines starting with space extend the previous line
                    # a line contaning a dot only is a newline
                    if line.strip() == ".":
                        results[name] = results[name] + "<br/><p>"
                    else:
                        results[name] = results[name] + " " + htmlize(line.strip())

        #print("results:", results)
        return results
                    
    def finished(self, code, status):
        if code == 0:
            if self.currentCmd == "pkgnames": # apt-cache pkgnames
                self.pkgnames = []
                for pkgname in self.results.split("\n"):
                    pkgname = pkgname.strip()
                    if len(pkgname) > 0:
                        self.pkgnames.append(pkgname)
                self.pkgnames.sort()
                self.list.setPacketList(self.pkgnames, self.installed)
            elif self.currentCmd == "search": # apt-cache search
                self.pkgnames = []
                # search also returns a description. We don't really
                # have space to display that ...
                for p in self.results.split("\n"):
                    if len(p.split()) > 1:
                        self.pkgnames.append(p.split()[0].strip())
                self.pkgnames.sort()
                self.search.setResult(self.pkgnames, self.installed)
            elif self.currentCmd == "show": # apt-cache show
                package = self.parseShowResults(self.results)                
                self.showPackageDialog(package)
            elif self.currentCmd == "-l": # dpkg -l
                self.installed = []
                for p in self.results.split("\n"):
                    parts = p.split()
                    if len(parts) >= 5:
                        flag,name,ver,arch = parts[0:4]
                        desc = " ".join(parts[4:])

                        # the arch flags allows some kind of sanity check
                        if arch == "all" or arch == "amd64" or arch == "i386" or arch == "armhf":
                            # ii are installed files
                            # rc are deinstalled files with config left
                            if flag == "ii":
                                #print(flag,name,ver,arch, desc)
                                self.installed.append(name.split(":")[0])
                        else:
                            print("Unsupported arch", arch)

                # we now have packages _and_ know the installed files
                # most installed packages should also be in pkgnames
                self.installed.sort()
            else:
                print("Current command unknown:", self.currentCmd)
        else:
            print("ERROR:", code)
            # TODO: display error message

        self.currentCmd = None
        self.busy.close()
        self.busy = None

    def do_cmd(self, cmd, parms):
        self.process  = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.processOutput)
        self.process.readyReadStandardError.connect(self.processError)
        self.process.finished.connect(self.finished)

        self.currentCmd = parms[0]
        self.results = ""
        self.process.start(cmd, parms )
            
        self.busy = BusyAnimation(self)
        self.busy.show()
        
    def apt_cache_cmd(self, parms):
        self.do_cmd(self.APT_CACHE, parms)

    def dpkg_cmd(self, parms):
        self.do_cmd(self.DPKG, parms)
        
class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)
        # create the empty main window
        self.w = TxtWindow("Apt")

        self.apt = AptWidget(self.w)
    
        self.vbox = QVBoxLayout()
        self.vbox.setContentsMargins(0,0,0,0)
        self.vbox.setSpacing(0)
        self.vbox.addWidget(self.apt)
        self.w.centralWidget.setLayout(self.vbox)

        self.w.show()
        self.exec_()
        
if __name__ == "__main__":
    FtcGuiApplication(sys.argv)

