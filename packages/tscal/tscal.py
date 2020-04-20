#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# TS-Cal -- An application to calibrate the touchscreen.
#
# Written in 2019 by Lars Heuer
#
# To the extent possible under law, the author(s) have dedicated all copyright
# and related and neighboring rights to this software to the public domain
# worldwide. This software is distributed without any warranty.
# You should have received a copy of the CC0 Public Domain Dedication along
# with this software.
#
# If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
#
"""TX-Pi TS-Calibration.

Executes the ``xinput_calibrator`` and shows a reboot dialog iff calibration
has changed.
"""
import os
import re
import sys
import subprocess
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from TouchStyle import TouchApplication, TouchWindow

# Must be writable by ftc user
_CALIB_FILE= "/usr/share/X11/xorg.conf.d/99-calibration.conf"

_CALIB_PATTERN = re.compile(r'^[\t ]*Option[\t ]+"Calibration"[\t ]+'
                            r'"(\d+)[ ]+(\d+)[ ]+(\d+)[ ]+(\d+)"'
                            r'[ ]*$', re.MULTILINE)


def calibrate():
    """\
    Shows the calibration dialog and returns whether the calibration was
    changed.

    :return: ``True`` if the calibration was updated, otherwise ``False``
    """
    proc = subprocess.Popen(["xinput_calibrator"], stdout=subprocess.PIPE)
    output, err = proc.communicate()
    m = _CALIB_PATTERN.search(output.decode('utf-8'))
    if not m:
        # Nothing to do. This is not an error, the user may have canceled the calibration
        return False
    calib_new = m.groups()
    with open(_CALIB_FILE, 'r') as f:
        calib_file_content = f.read()
    m = _CALIB_PATTERN.search(calib_file_content)
    if m:
        calib_old = m.groups()
    else:
        #TODO: This is an error: If the file does not contain any calibration information we cannot change it
        return False
    calib_changed = calib_new != calib_old
    if calib_changed:
        calib_file_content = re.sub(r'\d+[ ]+\d+[ ]+\d+[ ]+\d+', ' '.join(calib_new),
                                    calib_file_content)
        with open(_CALIB_FILE, 'w') as f:
            f.write(calib_file_content)
    return calib_changed


class TSCalApp(TouchApplication):
    """\
    Simple app which is mainly used to display a reboot dialog after the
    calibration was successful.
    """
    def __init__(self, args):
        super(TSCalApp, self).__init__(args)
        if calibrate():
            self._ask_for_reboot()
        else:
            self.close()

    def _ask_for_reboot(self):
        """\
        Shows a cancelable reboot dialog.
        """
        translator = QTranslator()
        if translator.load(QLocale.system(), os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                          'tscal_')):
            # Translation successfully loaded, install translator
            self.installTranslator(translator)
        win = TouchWindow(QCoreApplication.translate('TSCalApp', 'Reboot'))
        win.titlebar.setCancelButton()
        btn_reboot = QPushButton(QCoreApplication.translate('TSCalApp', 'Reboot'))
        btn_reboot.setObjectName('smalllabel')
        btn_reboot.clicked.connect(self._on_reboot)
        layout = QVBoxLayout()
        hbox = QHBoxLayout()
        hbox.addStretch()
        lbl = QLabel()
        lbl.setPixmap(QPixmap(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                            'reboot.png')))
        hbox.addWidget(lbl)
        hbox.addStretch()
        layout.addLayout(hbox)
        layout.addStretch()
        textfield = QTextEdit('<font size="2">{0}<br><br><font size="1">{1}' \
                            .format(QCoreApplication.translate('TSCalApp', "It's recommended to restart the device."),
                                    QCoreApplication.translate('TSCalApp', 'Do you want to reboot now?')))
        textfield.setObjectName("smalllabel")
        textfield.setAlignment(Qt.AlignCenter)
        textfield.setReadOnly(True)
        layout.addWidget(textfield)
        layout.addStretch()
        layout.addWidget(btn_reboot)
        win.centralWidget.setLayout(layout)
        win.show()
        #self.setCentralWidget(win)

    def _on_reboot(self):
        subprocess.call(['sudo', 'reboot'])


if __name__ == "__main__":
    TSCalApp(sys.argv).exec_()
