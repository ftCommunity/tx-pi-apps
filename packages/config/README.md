# TX-Pi-Config

This project provides a configuration application for the TX-Pi.


## Config panes

The configuarion dialogs are organized in "panes". Each
pane represents a specific configuration aspect. The context menu
is used to switch between the panes.

Each pane must have a name which is also used as menu entry.

The panes are registered in the constructor of the ``ConfigApp``. 

The abstract ``Pane`` class provides some helper methods, i.e.
``run_script`` to run a shell script within the ``scripts/`` directory.
The script is run by ``QProcess`` and should not block the GUI but
shows a busy animation on top of the screen. If the script is finished, 
a previously registered callback function is invoked.

Please note that all scripts in the ``scripts`` directory require 
root rights by default. Adding a script requires a modification of
the ``tx-pi-setup.sh`` script (see section ``/etc/sudoers.d/txpiconfig``).

If changing the configuration requires a reboot, the ``Pane`` provides
another helper function ``ask_for_reboot``. The user may cancel the
recommended reboot, though.


## Releases
If the develop branch is stable, create a release in the
master branch, tagged with a version number. 


## Note
Since the TX-Pi setup uses the master branch w/o any version number,
the master branch must be stable.
