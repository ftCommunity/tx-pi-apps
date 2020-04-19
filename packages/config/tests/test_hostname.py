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
"""Some tests regarding the hostname validation pattern.
"""
import pytest
from config import _HOSTNAME_PATTERN


@pytest.mark.parametrize('hostname', ['TX-Pi', 'xn--hreinprmlte-q8aad36aiad',
                                      'Tx-Pi2', '0Tx-Pi'])
def test_valid_hostname(hostname):
    assert _HOSTNAME_PATTERN.match(hostname) is not None


@pytest.mark.parametrize('hostname', ['txpi.', '-Pi', 'TX-', 'tx_pi', 'tx pi'])
def test_invalid_hostname(hostname):
    assert _HOSTNAME_PATTERN.match(hostname) is None


if __name__ == '__main__':
    pytest.main([__file__])
