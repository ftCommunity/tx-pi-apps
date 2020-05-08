#!/bin/bash
#
# Creates the config.zip
#
echo "Delete config.zip"
rm -f ./config.zip
echo "Create config.zip"
zip -r config.zip config.py config_*.qm manifest icon.png reboot.png LICENSE scripts
