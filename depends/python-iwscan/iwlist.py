#!/usr/bin/python -tt

__author__    = 'Kel Modderman'
__copyright__ = '(C) 2008 Kel Modderman <kel@otaku42.de>'
__license__   = 'GPLv2 or any later version'

import iwscan
import os
import sys

def printScanResults(results):
    '''Pretty print scan results from list of dicts returned by iwscan.'''
    for cellno, cell in enumerate(results):
        rj = ' ' * 10
        if cell.get('bssid'):
            print(rj + 'Cell %02d - Address: %s' % (cellno + 1, cell['bssid']))

        rj += ' ' * 10
        if cell.get('essid'):
            print(rj + 'ESSID:"%s"' % cell['essid'])

        if cell.get('protocol'):
            print(rj + 'Protocol:%s' % cell['protocol'])

        if cell.get('mode'):
            print(rj + 'Mode:%s' % cell['mode'])

        if cell.get('frequency') and cell.get('channel'):
            print(rj + 'Frequency:%s (Channel %d)' %
                  (cell['frequency'], cell['channel']))

        if cell.get('enc'):
            enc = 'on'
        else:
            enc = 'off'
        print(rj + 'Encryption key:%s' % enc)

        if cell.get('bitrate'):
            print(rj + 'Bit Rate:%s' % cell['bitrate'])

        if cell.get('stats'):
            print(rj + cell['stats'])

        if cell.get('ie'):
            ie = cell['ie']

            print(rj + 'IE: %s Version %d' % (ie['type'], ie['version']))

            ierj = rj + ' ' * 4

            if ie.get('group'):
                print(ierj + 'Group Cipher : %s' % ie['group'])

            if ie.get('pairwise'):
                print(ierj + 'Pairwise Ciphers (%d) : %s' %
                      (len(ie['pairwise']), ' '.join(ie['pairwise'])))

            if ie.get('auth'):
                print(ierj + 'Authentication Suites (%d) : %s' %
                      (len(ie['auth']), ' '.join(ie['auth'])))

        print


if __name__ == '__main__':
    try:
        print('python-iwscan v%d.%d.%d' % iwscan.version())
        print('iwlib v%d - wext v%d\n' % (iwscan.iw_version(),
                                          iwscan.we_version()))
        wi = iwscan.enum_devices()
        for w in wi:
            res = iwscan.WirelessInterface(w).Scan()
            if len(res) < 1:
                print("%-10sNo scan results." % w)
            else:
                print("%-10sScan completed :" % w)
                printScanResults(res)
    except iwscan.error, e:
        print("Error: %s" % e)
        sys.exit(1)
    else:
        if len(wi) < 1:
            print("No wireless devices detected!")
            sys.exit(1)
