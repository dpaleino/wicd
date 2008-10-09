#!/usr/bin/python

'''Example usage of the wpactrl extension.'''

__author__    = 'Kel Modderman'
__copyright__ = '(c) 2008 Kel Modderman <kel@otaku42.de>'
__license__   = 'GPLv2'

import os
import sys
import time
import wpactrl

run = '/var/run/wpa_supplicant'

if __name__ == "__main__":
    print '>>> wpactrl version %d.%d.%d ...' % wpactrl.version()

    sockets = []
    if os.path.isdir(run):
        try:
            sockets = [os.path.join(run, i) for i in os.listdir(run)]
        except OSError, error:
            print 'Error:', error
            sys.exit(1)

    if len(sockets) < 1:
        print 'No wpa_ctrl sockets found in %s, aborting.' % run
        sys.exit(1)

    for s in sockets:
        try:
            print '>>> # Open a ctrl_iface connection'
            print '>>> wpa = wpactrl.WPACtrl("%s")' % s
            wpa = wpactrl.WPACtrl(s)

            print '>>> # Location of ctrl_iface socket'
            print '>>> wpa.ctrl_iface_path'
            print wpa.ctrl_iface_path

            print '>>> # Request a few commands'
            print '>>> wpa.request("PING")'
            print wpa.request('PING')

            print '>>> wpa.request("STATUS")'
            print wpa.request('STATUS')

            print '>>> wpa.request("LIST_NETWORKS")'
            print wpa.request('LIST_NETWORKS')

            time.sleep(1)

            print '>>> # Open a new ctrl_iface connection for receiving event'
            print '>>> # messages'
            print '>>> wpa_event = wpactrl.WPACtrl("%s")' % s
            wpa_event = wpactrl.WPACtrl(s)

            print '>>> wpa_event.attached'
            print wpa_event.attached
            print '>>> wpa_event.attach()'
            wpa_event.attach()
            print '>>> wpa_event.attached'
            print wpa_event.attached

            print '>>> # Request commands via original ctrl_iface connection'
            print '>>> wpa.request("SCAN")'
            print wpa.request('SCAN')

            time.sleep(1)

            print '>>> wpa.request("STATUS")'
            print wpa.request('STATUS')

            print '>>> # Waiting 10s for pending events ...'
            time.sleep(10)

            print '>>> # Check for pending events and collect them'
            print '>>> while wpa_event.pending():'
            print '>>> ....wpa_event.recv()'
            while wpa_event.pending():
                print wpa_event.recv()

            print '>>> # Request scan results (wpa_supplicant only)'
            print '>>> results = wpa.scanresults()'
            print '>>> for no, bss in enumerate(results):'
            print '>>> ....print \'bss(%d):\' % no'
            print '>>> ....print bss'
            results = wpa.scanresults()
            for no, bss in enumerate(results):
                print 'bss(%d):' % no
                print bss

            print '>>> # Detach the event monitor'
            print '>>> wpa_event.detach()'
            wpa_event.detach()

            print '>>> # Finished!'
        except wpactrl.error, error:
            print 'Error:', error
            pass
