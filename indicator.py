#!/usr/bin/python3

from gi.repository import Gtk as Gtk
from gi.repository import GLib as GLib
from gi.repository import AppIndicator3 as AppIndicator
import sys
import os
import re

class LsyncdIndicator:
    def __init__(self):
        self.ind = AppIndicator.Indicator.new_with_path(
            "my-custom-indicator",
            "bluespinner",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
            os.path.dirname(os.path.realpath(__file__)) + '/icons/')
        self.menu_setup()
        self.ind.set_menu(self.menu)
        self.ind.set_property('label-guide', 'LSYNCD')
        self.lastSeekPosition = 0
        self.syncQueue = []
        self.lastLineType = ''

    def menu_setup(self):
        self.menu = Gtk.Menu()
        self.quit_item = Gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()
        self.menu.append(self.quit_item)
        # self.ind.set_label('lsyncd', 'LSYNCD')

    def main(self):
        self.logfile = open('/var/log/lsyncd/lsyncd.log', mode='rb')
        GLib.timeout_add(150, self.monitor_lsyncd)
        GLib.MainLoop().run()

    def quit(self, menuObj):
        GLib.MainLoop().quit()
        sys.exit(0)

    def monitor_lsyncd(self):
        lastLine = self.tail_log()
        if (lastLine == ''):
            return True

        print ("printing the sync queue: " + self.lineType, self.syncQueue)
        # Found a match that a sync is happening
        if (self.lineType == 'FINISHED' and len(self.syncQueue) == 0):
            self.ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            self.ind.set_icon('bluespinner')
            self.ind.set_label('idle', 'LSYNCD')
        elif (self.lineType == 'FINISHED' and len(self.syncQueue) > 0):
            pass
        elif (self.lineType == 'SYNCING'):
            self.ind.set_icon('greenspinner')
            self.ind.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            self.ind.set_label('sync', 'LSYNCD')
        elif (self.lineType == 'LSYNCD TERMINATED'):
            self.ind.set_icon('redep')
            self.ind.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            self.ind.set_label('no lsyncd', 'LSYNCD')
        elif (self.lineType == 'ERROR'):
            self.ind.set_icon('redep')
            self.ind.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            self.ind.set_label('error', 'LSYNCD')
        else:
            print ("unknown something happening. Update some regular expressions")

        return True

    def tail_log(self, lines=1):
        # Keep track of the number of bytes has been written to the log file since the last loop
        amountToSeek = 0
        endOfFileByte = self.logfile.seek(0, 2)
        if (self.lastSeekPosition != endOfFileByte):
            amountToSeek = self.logfile.tell() - self.lastSeekPosition
            self.lastSeekPosition = self.logfile.tell()

        # print (self.lastSeekPosition, endOfFileByte, amountToSeek)
        # If this is the first run, the amount to seek will be the entire file.
        if (self.lastSeekPosition != amountToSeek):
            self.logfile.seek(-amountToSeek, 1)
        elif (self.lastSeekPosition == amountToSeek):
            self.logfile.seek(-200, 2)

        line = self.logfile.readline().decode().rstrip()
        lastLine = line
        while line != '':
            lastLine = line
            self.lastSeekPosition = self.logfile.tell()
            self.lineType = self.get_type_of_line(line);
            if (self.lineType == 'FINISHED' and len(self.syncQueue) > 0):
                self.syncQueue.pop()
            elif (self.lineType == 'STARTING SYNC'):
                self.syncQueue.append(self.lineType)

            line = self.logfile.readline().decode().rstrip()

        return lastLine

    def get_type_of_line(self, lastLine):
        if (re.search('exitcode: 0$', lastLine) or re.search('finished\.$', lastLine)):
            return 'FINISHED'
        elif (re.search('Calling rsync with', lastLine) or re.search('recursive startup rsync', lastLine)):
            return 'STARTING SYNC'
        elif (re.search('/$', lastLine) or re.search('[\*\w]\.\w+$', lastLine)):
            return 'SYNCING'
        elif (re.search('TERM signal, fading ---', lastLine)):
            return 'LSYNCD TERMINATED'
        elif (re.search('error|Error', lastLine)):
            return 'ERROR'
        else:
            return 'UNKNOWN'

if __name__ == "__main__":
    indicator = LsyncdIndicator()
    indicator.main()