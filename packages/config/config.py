#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Config -- An application to configure a TX-Pi.
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
"""TX-Pi Configuration - Copyright (c) 2019 -- Lars Heuer
"""
import os
import re
import sys
import subprocess
import configparser
from collections import namedtuple
from functools import partial
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from TouchStyle import TouchApplication, TouchWindow, TouchMessageBox
try:
    from TouchStyle import BusyAnimation
except ImportError:
    from launcher import BusyAnimation


_parser = configparser.ConfigParser()
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'manifest'), encoding='utf-8') as f:
    _parser.read_file(f)

__version__ = _parser.get('app', 'version', fallback='n/a')

del _parser


def app_path():
    """\
    Returns the path of the application directory.
    """
    return os.path.dirname(os.path.realpath(__file__))


class ConfigApp(TouchApplication):
    """Application to configure the TX-Pi.
    """
    def __init__(self, args):
        super(ConfigApp, self).__init__(args)
        translator = QTranslator()
        if translator.load(QLocale.system(), os.path.join(app_path(), 'config_')):
            # Translation successfully loaded, install translator
            self.installTranslator(translator)
        win = TouchWindow(QCoreApplication.translate('ConfigApp', 'Config'))
        self.win = win
        self._busy_animation = None
        menu = win.addMenu()
        container = PaneContainer(self, menu=menu)
        # Register config panes
        container.add_pane(ServicesPane(container))
        container.add_pane(HostnamePane(container))
        container.add_pane(DisplayPane(container))
        win.setCentralWidget(container)
        win.show()
        self.exec_()

    def iambusy(self, busy):
        """\
        Indicates that the app is (not) busy.

        If the app is busy, the window will be blurred and a busy animation is
        shown on top of the window.

        See also ``_busy`` and ``_blur_window``

        :param bool busy: ``True`` to indicate that the app is busy, otherwise ``False``.
        """
        self._blur_window(busy)
        self._busy(busy)

    def _busy(self, busy):
        """\
        Shows / disables a busy animation.

        :type busy: bool
        :param busy: ``True`` to show a busy animation, ``False`` to stop the animation.
        """
        if busy and self._busy_animation is None:
            self._busy_animation = BusyAnimation(self, self.win)
            self._busy_animation.show()
        elif not busy and self._busy_animation is not None:
            self._busy_animation.close()
            self._busy_animation = None

    def _blur_window(self, blur):
        """Blurs the window.

        :type blur: bool
        :param blur: ``True`` to enable blurring effect, ``False`` to disable blurring.
        """
        # Since the graphic effect is owned by the widget, two effects are needed.
        cw_effect, tb_effect = None, None
        if blur:
            cw_effect = QGraphicsBlurEffect(self)
            tb_effect = QGraphicsBlurEffect(self)
        self.win.centralWidget.setGraphicsEffect(cw_effect)
        self.win.titlebar.setGraphicsEffect(tb_effect)


class PaneContainer(QStackedWidget):
    """\
    Container for panes.
    """
    def __init__(self, app, menu):
        """\
        Initializes the pane with a default pane.

        :param parent: An instance of TouchApplication
        :param menu: The context menu. It's used to add items to switch between
                     the panes.
        """
        super(PaneContainer, self).__init__()
        self._menu = menu
        self._app = app
        startpane = QWidget()
        layout = QVBoxLayout()
        lbl = QLabel()
        lbl.setPixmap(QPixmap(os.path.join(app_path(), 'icon.png')))
        layout.addLayout(PaneContainer._hcenter_widget(lbl))
        layout.addWidget(QLabel(''))
        lbl = QLabel(QCoreApplication.translate('ConfigApp', 'Welcome'))
        lbl.setObjectName('smalllabel')
        layout.addLayout(PaneContainer._hcenter_widget(lbl))
        lbl = QLabel(QCoreApplication.translate('ConfigApp', 'Please choose an item from the menu.'))
        lbl.setObjectName('tinylabel')
        lbl.setWordWrap(True)
        layout.addLayout(PaneContainer._hcenter_widget(lbl))
        layout.addStretch()
        startpane.setLayout(layout)
        self.addWidget(startpane)

    @staticmethod
    def _hcenter_widget(widget):
        """\
        Centers the provided widget horizontally.

        :return: QHBoxLayout with the provided widget.
        """
        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(widget)
        hbox.addStretch()
        return hbox

    def add_pane(self, pane):
        """\
        Adds a pane and registers the pane within the menu.

        :param pane: The pane to add.
        """
        idx = self.addWidget(pane)
        action = self._menu.addAction(pane.name)
        action.triggered.connect(partial(self._show_pane, index=idx))

    def _show_pane(self, index):
        """\
        Called to switch panes.

        :param int index: Index of the pane to switch to.
        """
        switch = True
        if self.currentIndex() != 0:
            switch = self.currentWidget().validate()
        if switch:
            self.widget(index).before_focus()
            self.setCurrentIndex(index)
            self.widget(index).has_focus()


class Pane(QWidget):
    """\
    A Pane is a page within the PaneContainer.

    A pane may be invisible or visible.

    Inherit from this class for additional config pages and register them
    in the ConfigApp's constructor.
    """
    def __init__(self, parent, name):
        """\
        Initializes the pane.

        :param name: The name of the pane. The name will also be used as menu
                     item. The name should have been translated.
        """
        super(Pane, self).__init__(parent)
        self.name = name
        self._app = None

    def run_script(self, name, args, callback):
        """\
        Runs the script with the provided name as background process
        and informs `callback` about the result.

        :param str name: The script name.
        :param list args: A list of arguments (strings)
        :param callback: A function accepting the arguments ``exit_code`` and ``exit_status``
        """
        def on_script_finished(exit_code, exit_status):
            self.parent()._app.iambusy(False)
            callback(exit_code, exit_status)

        self.parent()._app.iambusy(True)
        script = os.path.join(app_path(), 'scripts', name)
        proc = QProcess(self)
        proc.finished.connect(on_script_finished)
        proc.start('sudo {0} {1}'.format(script, ' '.join(args)))

    def ask_for_reboot(self):
        """\
        Opens a dialog which recommends to reboot the device to apply changes.

        The user may cancel the reboot, though.
        """
        dlg = TouchMessageBox(QCoreApplication.translate('ConfigApp', 'Reboot'), self)
        dlg.setCancelButton()
        dlg.addPixmap(QPixmap(os.path.join(app_path(), 'reboot.png')))
        dlg.setText('<font size="2">{0}<br><br><font size="1">{1}' \
                            .format(QCoreApplication.translate('ConfigApp', "It's recommended to restart the device."),
                                    QCoreApplication.translate('ConfigApp', 'Do you want to reboot now?')))
        dlg.setPosButton(QCoreApplication.translate('ConfigApp', 'Reboot'))
        res, txt = dlg.exec_()
        if res:
            subprocess.call(['sudo', 'reboot'])

    def before_focus(self):
        """\
        Method called from PaneContainer right before activating this pane.

        Does nothing by default.
        """
        pass

    def has_focus(self):
        """\
        Method called from PaneContainer to indicate that this pane is active.

        Does nothing by default.
        """
        pass

    def validate(self):
        """\
        Method called from PaneContainer to indicate that this pane will be
        moved to the background.

        If this method returns ``False``, the pane stays at the top and the
        requested pane change is canceled.

        This method can be used to remind the user that the pane contains
        unsaved changes etc.

        Note: This method may not be called if the application is closed.

        Does nothing by default but returns ``True`` to allow pane changes.
        """
        return True


# Service names
_SERVICE_SSH = 'ssh'
_SERVICE_VNC = 'x11vnc'


class ServicesPane(Pane):
    """\
    Pane to configure services.
    """
    def __init__(self, parent):
        super(ServicesPane, self).__init__(parent, name=QCoreApplication.translate('ConfigApp', 'Services'))
        self._cb_ssh = QCheckBox(QCoreApplication.translate('ConfigApp', 'SSH server'))
        self._cb_vnc = QCheckBox(QCoreApplication.translate('ConfigApp', 'VNC server'))
        self._cb_i2c = QCheckBox(QCoreApplication.translate('ConfigApp', 'I2C bus'))
        layout = QVBoxLayout()
        lbl = QLabel(QCoreApplication.translate('ConfigApp', 'Services'))
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(self._cb_ssh)
        layout.addStretch()
        layout.addWidget(self._cb_vnc)
        layout.addStretch()
        layout.addWidget(self._cb_i2c)
        layout.addStretch()
        lbl = QLabel(QCoreApplication.translate('ConfigApp', 'The state of the services is persistent: It remains after shutdown.'))
        lbl.setWordWrap(True)
        lbl.setObjectName('tinylabel')
        layout.addWidget(lbl)
        self.setLayout(layout)
        self._cb_ssh.toggled.connect(lambda checked: self._toggle_service(_SERVICE_SSH, checked))
        self._cb_vnc.toggled.connect(lambda checked: self._toggle_service(_SERVICE_VNC, checked))
        self._cb_i2c.toggled.connect(lambda checked: self._toggle_i2c(checked))

    def before_focus(self):
        """\
        Update check boxes.
        """
        self._update_current_service_status()

    def _set_gui_elements_enabled(self, enabled):
        """\
        Enables / disables the checkboxes and blocks / unblocks the signals.

        :param bool enabled: ``True`` to enable all GUI elements and let them emit signals;
                             ``False`` to disable all GUI elements and to omit signals.
        """
        self._cb_ssh.setEnabled(enabled)
        self._cb_vnc.setEnabled(enabled)
        self._cb_i2c.setEnabled(enabled)
        # Block signals if enabled is False to avoid a "toggled" signal if the
        # "checked" state is changed via code
        self._cb_ssh.blockSignals(not enabled)
        self._cb_vnc.blockSignals(not enabled)
        self._cb_i2c.blockSignals(not enabled)

    def _update_current_service_status(self):
        """\
        Updates the the internal state and the checkboxes acc. to the current
        status of the services.
        """
        self._set_gui_elements_enabled(False)
        ssh_enabled = self._get_service_status(_SERVICE_SSH)
        vnc_enabled = self._get_service_status(_SERVICE_VNC)
        i2c_enabled = self._get_i2c_status()
        self._cb_ssh.setChecked(ssh_enabled)
        self._cb_vnc.setChecked(vnc_enabled)
        self._cb_i2c.setChecked(i2c_enabled)
        self._set_gui_elements_enabled(True)

    @staticmethod
    def _get_service_status(service_name):
        """\
        Returns the service status for the provided service.

        :param name: Service name
        :return: Boolean value if the service is active or not.
        """
        proc = subprocess.Popen(['systemctl', 'status',  service_name],
                                stdout=subprocess.PIPE)
        output, err = proc.communicate()
        return b'Active: active (running)' in output

    @staticmethod
    def _get_i2c_status():
        """\
        Returns if the I2C bus is enabled.

        :return: Boolean value if the I2C bus is enabled or not.
        """
        with open('/boot/config.txt', 'r') as f:
            return re.search(r'^(device_tree_param|dtparam)=([^,]*,)*i2c(_arm)?(=(on|true|yes|1))?(,.*)?$',
                             f.read(), re.MULTILINE) is not None

    def _toggle_service(self, service_name, enable):
        """\
        Enable / disable the provided service.

        If enabled, systemd enables and starts the service; otherwise the
        service is disabled and stopped.

        :param service_name: The service name.
        :param bool enable: Boolean indicating if the service should become enabled.
        """
        self._set_gui_elements_enabled(False)
        self.run_script(service_name, [('enable' if enable else 'disable')],
                        self._on_toggle_finished)

    def _toggle_i2c(self, enable):
        """
        Toggles the I2C bus.

        :param bool enable: Boolean if the I2C bus should be enabled.
        """
        def on_toggled(exit_code, exit_status):
            """\
            Special "toggle finished" function which displays a reboot dialog
            iff toggling was successful.
            """
            self._on_toggle_finished(exit_code, exit_status)
            if exit_code == 0:
                self.ask_for_reboot()

        self._set_gui_elements_enabled(False)
        self.run_script('i2cbus', [('enable' if enable else 'disable')],
                        on_toggled)

    def _on_toggle_finished(self, exit_code, exit_status):
        """\
        Called when a service was enabled / disabled.

        :param exit_code:
        :param exit_status:
        """
        if exit_code == 0:
            self._set_gui_elements_enabled(True)
        else:
            # Something went wrong, update the current state of the services
            self._update_current_service_status()


_HOSTNAME_PATTERN = re.compile(r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$')

class HostnamePane(Pane):
    """\
    Pane to configure the hostname.
    """
    def __init__(self, parent):
        super(HostnamePane, self).__init__(parent, name=QCoreApplication.translate('ConfigApp', 'Hostname'))
        self._edit_hostname = QLineEdit(self)
        self._btn_apply = QPushButton(QCoreApplication.translate('ConfigApp', 'Apply'))
        self._btn_apply.clicked.connect(self._on_apply)
        layout = QVBoxLayout()
        lbl = QLabel(QCoreApplication.translate('ConfigApp', 'Hostname'))
        layout.addWidget(lbl)
        layout.addWidget(self._edit_hostname)
        layout.addStretch()
        layout.addWidget(self._btn_apply)
        self.setLayout(layout)
        # The event "textEdited" does not work if the TouchStyle keyboard shows up
        self._edit_hostname.textChanged.connect(self._on_hostname_edited)

    def before_focus(self):
        """\
        Update hostname.
        """
        self._retrieve_hostname()

    def _retrieve_hostname(self):
        """\
        Reads the current hostname and updates the edit box with the current
        hostname.
        """
        self._edit_hostname.setEnabled(False)
        self._btn_apply.setEnabled(False)
        self._edit_hostname.setText(self._get_hostname())
        self._edit_hostname.setEnabled(True)
        # Will be enabled if text changes, see _on_hostname_edited
        self._btn_apply.setEnabled(False)

    @staticmethod
    def _get_hostname():
        """\
        Returns the current hostname as string.
        """
        with open('/etc/hostname', 'r') as f:
            return f.read().strip()

    def _on_hostname_edited(self, txt):
        """\
        Checks if the `txt` looks like a valid hostname and enables / disables
        the "Apply" button.
        """
        self._btn_apply.setEnabled(_HOSTNAME_PATTERN.match(txt) is not None)

    def _on_apply(self):
        """\
        Called to save a changed hostname.
        """
        self._edit_hostname.setEnabled(False)
        self._btn_apply.setEnabled(False)
        self.run_script('hostname', [self._edit_hostname.text()],
                        self._on_apply_finished)

    def _on_apply_finished(self, exit_code, exit_status):
        """\
        Called when the hostname change was finished.

        :param exit_code:
        :param exit_status:
        """
        if exit_code == 0:
            self._edit_hostname.setEnabled(True)
            self.ask_for_reboot()
        else:
            # Something went wrong
            self._retrieve_hostname()



_DISPLAY_PATTERN = re.compile(r'^dtoverlay=(waveshare[^:\n]+):?'
                              r'(?:,?(?:rotate=([0-9]+))|,?(?:speed=([0-9]+))|,?(?:fps=([0-9]+)))*$',
                              re.MULTILINE)

# Used to read / set the display configuration
DisplayConfig = namedtuple('DisplayConfig', ['driver', 'rotation', 'speed', 'fps'])

def _parse_display_config(s):
    """\
    Reads the display configuration from string `s` and returns a `DisplayConfig`
    instance.

    :param str s: Content of /boot/config.txt
    :return: A DisplayConfig instance with containing the display configuration.
    """
    m = _DISPLAY_PATTERN.search(s)
    if not m:
        return None
    driver, rotation, speed, fps = m.groups()
    return DisplayConfig(driver=driver, rotation=(int(rotation) if rotation else None),
                         speed=(int(speed) if speed else None),
                         fps=(int(fps) if fps else None))


class DisplayPane(Pane):
    """\
    Pane to configure the display.
    """
    def __init__(self, parent):
        super(DisplayPane, self).__init__(parent, QCoreApplication.translate('ConfigApp', 'Display'))
        self._btn_apply = QPushButton(QCoreApplication.translate('ConfigApp', 'Apply'))
        self._btn_apply.clicked.connect(self._on_apply)
        self._rotation = QComboBox(self)
        self._rotation.addItems(['0', '90', '180', '270'])
        self._speed = QSpinBox(self)
        self._speed.setRange(16, 125)
        self._fps = QSpinBox(self)
        self._fps.setMaximum(50)
        layout = QVBoxLayout()
        lbl = QLabel(QCoreApplication.translate('ConfigApp', 'Display'))
        layout.addWidget(lbl)
        layout.addStretch()
        lbl = QLabel(QCoreApplication.translate('ConfigApp', 'Rotation'))
        lbl.setObjectName('smallerlabel')
        layout.addWidget(lbl)
        layout.addWidget(self._rotation)
        lbl = QLabel(QCoreApplication.translate('ConfigApp', 'SPI speed (MHz)'))
        lbl.setObjectName('smallerlabel')
        layout.addWidget(lbl)
        layout.addWidget(self._speed)
        lbl = QLabel(QCoreApplication.translate('ConfigApp', 'Frames per second'))
        lbl.setObjectName('smallerlabel')
        layout.addWidget(lbl)
        layout.addWidget(self._fps)
        layout.addStretch()
        layout.addWidget(self._btn_apply)
        self.setLayout(layout)

    def before_focus(self):
        """\
        Update GUI elements.
        """
        self._retrieve_display_config()

    def _retrieve_display_config(self):
        """\
        Reads the display config and updates the GUI elements accordingly.
        """
        self._rotation.setEnabled(False)
        self._speed.setEnabled(False)
        self._fps.setEnabled(False)
        self._btn_apply.setEnabled(False)
        config = self._parse_config()
        self._rotation.setCurrentIndex(1)
        if config.rotation is not None:  # Check for None since 0 is a valid value
            idx = self._rotation.findText(str(config.rotation))
            if idx > -1:
                self._rotation.setCurrentIndex(idx)
        self._speed.setValue(16)
        if config.speed:
            # Convert speed to MHz
            self._speed.setValue(config.speed // 1000000)
        self._fps.setValue(0)
        if config.fps:
            self._fps.setValue(config.fps)
        self._rotation.setEnabled(True)
        self._speed.setEnabled(True)
        self._fps.setEnabled(True)
        self._btn_apply.setEnabled(True)

    @staticmethod
    def _parse_config():
        """\
        Reads /boot/config.txt and parses the display config.

        Returns an instance of DisplayConfig
        """
        with open('/boot/config.txt', 'r') as f:
            return _parse_display_config(f.read())

    def _on_apply(self):
        """\
        Called to save the display config.
        """
        rotation = self._rotation.currentText()
        speed = self._speed.value()
        fps = self._fps.value()
        self._rotation.setEnabled(False)
        self._speed.setEnabled(False)
        self._fps.setEnabled(False)
        self._btn_apply.setEnabled(False)
        # Provide alwas all three params even if they're empty
        self.run_script('display', [rotation, str(speed), str(fps)], self._on_apply_finished)

    def _on_apply_finished(self, exit_code, exit_status):
        """\
        Called when display changes were finished.

        :param exit_code:
        :param exit_status:
        """
        if exit_code == 0:
            self._rotation.setEnabled(True)
            self._speed.setEnabled(True)
            self._fps.setEnabled(True)
            self._btn_apply.setEnabled(True)
            self.ask_for_reboot()
        else:
            # Something went wrong
            self._retrieve_display_config()


if __name__ == "__main__":
    ConfigApp(sys.argv)
