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
"""Some tests regarding display config.
"""
import os
import importlib
import pytest
from config import _parse_display_config


@pytest.mark.parametrize('s,expected', [('dtoverlay=waveshare35b-v2:rotate=180\n', ('waveshare35b-v2', 180, None, None)),
                                        ('dtoverlay=waveshare35b-v2\n', ('waveshare35b-v2', None, None, None)),
                                        ('dtoverlay=waveshare35a:rotate=180\n', ('waveshare35a', 180, None, None)),
                                        ('dtoverlay=waveshare35a:rotate=180,speed=40000000\n', ('waveshare35a', 180, 40000000, None)),
                                        ('dtoverlay=waveshare35a:rotate=180,speed=40000000,fps=50\n', ('waveshare35a', 180, 40000000, 50)),
                                        ('dtoverlay=waveshare35a:speed=40000000,fps=50\n', ('waveshare35a', None, 40000000, 50)),
                                        ('dtoverlay=waveshare35a:speed=40000000\n', ('waveshare35a', None, 40000000, None)),
                                        ('dtoverlay=waveshare35a:speed=40000000,rotate=90\n', ('waveshare35a', 90, 40000000, None)),
                                        ('dtoverlay=waveshare35a:fps=24,speed=27000000,rotate=90\n', ('waveshare35a', 90, 27000000, 24)),
                                        ])
def test_parse_displayconfig(s, expected):
    res = _parse_display_config(s)
    assert res
    assert expected == tuple(res)


# 3.2"
DISPLAY_32_0   = (219, 3835, 219, 3984)
DISPLAY_32_90  = (3835, 219, 219, 3984)
DISPLAY_32_180 = (3835, 219, 3984, 219)
DISPLAY_32_270 = (219, 3835, 3984, 219)

# 3.5" A / B
DISPLAY_35_0   = (300, 3932, 294, 3801)
DISPLAY_35_90  = (3932, 300, 294, 3801)
DISPLAY_35_180 = (3932, 300, 3801, 294)
DISPLAY_35_270 = (300, 3932, 3801, 294)

@pytest.mark.parametrize('calib,rotate,expected', [
                                        # Examples from 3.5" A/B
                                        (DISPLAY_35_180, 180, DISPLAY_35_180),
                                        (DISPLAY_35_180,  90, DISPLAY_35_90),
                                        (DISPLAY_35_180, 270, DISPLAY_35_270),
                                        (DISPLAY_35_180,   0, DISPLAY_35_0),
                                        # Examples from 3.2"
                                        (DISPLAY_32_270,   0, DISPLAY_32_0),
                                        (DISPLAY_32_270,  90, DISPLAY_32_90),
                                        (DISPLAY_32_270, 180, DISPLAY_32_180),
                                        (DISPLAY_32_270, 270, DISPLAY_32_270),
                                        (DISPLAY_32_90,    0, DISPLAY_32_0),
                                        (DISPLAY_32_180,  90, DISPLAY_32_90),
                                        (DISPLAY_32_0,   180, DISPLAY_32_180),
                                        (DISPLAY_32_90,  270, DISPLAY_32_270),
                                        ])
def test_calibration(calib, rotate, expected):
    # Load display script from scripts directory
    display = importlib.machinery.SourceFileLoader('display',
                                                   os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                '../scripts/display')) \
                                                    .load_module()
    assert display
    assert expected == display.calc_calibration(calib, rotate)


if __name__ == '__main__':
    pytest.main([__file__])
