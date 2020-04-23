#!/usr/bin/env python3
#-*- coding:utf-8 -*-

from TxtStyle import *
import sys, bisect

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
        pix.fill(Qt.transparent);
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
        self.searchResults.setPacketList(packages, installed)

class AppDialog(TouchDialog):
    request = pyqtSignal(str, str)
    
    def __init__(self, package, parent):
        TouchDialog.__init__(self, package["Package"], parent)

        self.package = package
        
        menu = self.addMenu()
        menu_inst = menu.addAction(QCoreApplication.translate("Menu", "Install"))
        menu_inst.triggered.connect(self.on_install)
        menu_remove = menu.addAction(QCoreApplication.translate("Menu", "Remove"))
        menu_remove.triggered.connect(self.on_remove)
        menu_purge = menu.addAction(QCoreApplication.translate("Menu", "Purge"))
        menu_purge.triggered.connect(self.on_purge)
        
        text = QTextEdit()
        text.setReadOnly(True)
        for i in package:
            text.append('<h3><font color="#fcce04">'+i+'</font></h3>'+package[i]+"\n")
        text.moveCursor(QTextCursor.Start)
        self.setCentralWidget(text)

    def on_install(self):
        self.request.emit("install", self.package["Package"])

    def on_remove(self):
        self.request.emit("remove", self.package["Package"])

    def on_purge(self):
        self.request.emit("purge", self.package["Package"])

class AptDialog(TouchDialog):
    cmdControl = pyqtSignal(str)
        
    def __init__(self, title, parent):
        TouchDialog.__init__(self, title, parent)
        vboxw = QWidget()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0,0,0,0)
        vbox.setSpacing(0)
        vboxw.setLayout(vbox)

        # text widget for command output
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.moveCursor(QTextCursor.Start)
        vbox.addWidget(self.text)

        # buttons for control
        self.hboxw = QWidget()
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0,0,0,0)
        hbox.setSpacing(0)
        self.hboxw.setLayout(hbox)

        yesBtn = QPushButton("Yes", self)
        yesBtn.clicked.connect(self.sendYes)
        hbox.addWidget(yesBtn)
        noBtn = QPushButton("No", self)
        noBtn.clicked.connect(self.sendNo)
        hbox.addWidget(noBtn)
        
        vbox.addWidget(self.hboxw)
        
        self.setCentralWidget(vboxw)

    def sendYes(self):
        self.cmdControl.emit("yes")
        
    def sendNo(self):
        self.cmdControl.emit("no")
        
    def cmdFinished(self, code):
        if code == 0:
            self.text.append("\nCommand finished successfully")
        else:
            self.text.append("\n<font color='red'><b>Return code:"+str(code)+"</b></font>")
        
        # disable the entire hbox as there's nothing to control
        # anymore
        self.hboxw.setEnabled(False)
        
    def getText(self):
        return self.text
        
class AptWidget(QWidget):
    cmdFinished = pyqtSignal(int)
    
    APT_CACHE = "/usr/bin/apt-cache"
    APT_GET = "/usr/bin/apt-get"
    DPKG = "/usr/bin/dpkg"

    def onCommand(self, cmd):
        if cmd == "List all":
            self.setContentPacketList(self)
            self.apt_cache_cmd(['pkgnames'])
        elif cmd == "Search":
            self.setContentSearch(self)
        elif cmd == "Update":
            self.setContentAptText(self)
            self.apt_get_cmd(["-y", "update"])
        elif cmd == "Upgrade":
            self.setContentAptText(self)
            self.apt_get_cmd(["-y", "upgrade"])
        elif cmd == "Autoremove":
            self.setContentAptText(self)
            self.apt_get_cmd(["-y", "autoremove"])
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
        self.apt_cache_cmd(["show", pkgname])
        
    def doSearch(self, str):
        self.apt_cache_cmd(["search", str ] )
        
    def setContentAptText(self, parent):
        self.removeOldContent()
        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        self.vbox.addWidget(self.text)
        self.content = self.text

    def setContentString(self, str, parent):
        self.removeOldContent()        
        self.label = QLabel(str, parent)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
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
        self.combo.addItem("Upgrade")
        self.combo.addItem("Autoremove")
        self.combo.activated[str].connect(self.onCommand)
        self.combo.setCurrentIndex(-1)
        self.vbox.addWidget(self.combo)
        
        # add empty content widget
        self.content = None
        self.setContentString("Please choose a command!", self)

        self.setLayout(self.vbox)        
        self.busy = None

        # immediately scan for installed apps
        self.dpkg_cmd(["-l"])
        
    def processError(self):
        pass
        
    def processOutput(self):
        results = bytes(self.process.readAllStandardOutput()).decode()
        if self.currentCmd.endswith("apt-get"):
            self.text.append(results)
        else:            
            self.results = self.results + results

    def showPackageDialog(self, package):
        # make sure we register this as a child window of the root
        self.appDialog = AppDialog(package, self.parent().parent())
        self.appDialog.request.connect(self.appRequest)
        self.appDialog.exec_()

    def appRequest(self, cmd, pkg):
        # open a apt text dialog
        dialog = AptDialog(cmd, self.appDialog)
        self.text = dialog.getText()

        # make sure the dialog notices when the command finishs
        self.cmdFinished.connect(dialog.cmdFinished)
        dialog.cmdControl.connect(self.appControl)

        self.apt_get_cmd([cmd, pkg])
        dialog.exec_()

        # update internal list of installed packages
        self.dpkg_cmd(["-l"])

    def appControl(self, c):
        if c == "yes":
            self.process.write("y\n".encode())
        elif c == "no":
            self.process.write("n\n".encode())
        else:
            print("unexpected control:", c)
        
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
                self.cmd_done()
                self.showPackageDialog(package)
                return
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
                                self.installed.append(name.split(":")[0])

                # we now have packages _and_ know the installed files
                # most installed packages should also be in pkgnames
                self.installed.sort()
            elif self.currentCmd.endswith("apt-get"): # sudo apt-get ...
                pass
            else:
                print("Current command unknown:", self.currentCmd)
        else:
            print("ERROR:", code)
            # TODO: display error message

        self.cmd_done()
        self.cmdFinished.emit(code)
                
    def cmd_done(self):            
        self.currentCmd = None
        self.busy.close()
        self.busy = None
        self.combo.setEnabled(True)        
        
    def do_cmd(self, cmd, parms):
        self.process  = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.processOutput)
        self.process.readyReadStandardError.connect(self.processError)
        self.process.finished.connect(self.finished)

        self.currentCmd = parms[0]
            
        self.results = ""
        self.process.start(cmd, parms )
            
        self.combo.setEnabled(False)
        self.busy = BusyAnimation(self)
        self.busy.show()
        
    def apt_cache_cmd(self, parms):
        self.do_cmd(self.APT_CACHE, parms)

    def apt_get_cmd(self, parms):
        cmd = [ self.APT_GET ]
        cmd.extend(parms)
        self.do_cmd("sudo", cmd)

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

