#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as Gtk
from gi.repository import GLib as GLib
gi.require_version('AppIndicator3', '0.1')
# gi.require_version('AppIndicator7', '1')
# import appindicator
from gi.repository import AppIndicator3 as AppIndicator
import sys
import os
import re
import logging
import math
import argparse

parser = argparse.ArgumentParser(description='Initialize a unity lsyncd indicator')
parser.add_argument('-l', '--loglevel', dest='loglevel', help='Options: DEBUG, INFO, WARNING, ERROR, CRITCAL')
args = parser.parse_args()

numeric_level = 50
if (args.loglevel):
    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        print ("Incorrect parameter for loglevel. Defaulting to WARNING")
        numeric_level = 30 # Default to warnings

logging.basicConfig(level=numeric_level)

class LsyncdIndicator:
    def __init__(self):
        self.ind = AppIndicator.Indicator.new_with_path(
            "my-custom-indicator",
            "bluespinner",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
            os.path.dirname(os.path.realpath(__file__)) + '/icons/')
        self.menu_setup()
        self.ind.set_menu(self.menu)
        self.lastSeekPosition = 0
        self.syncQueue = []
        self.lineType = ''
        self.indicatorIconIndex = 1

    def menu_setup(self):
        self.menu = Gtk.Menu()
        self.quit_item = Gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()

        self.test_item = Gtk.MenuItem("Open Config")
        self.test_item.connect("activate", self.open_config)
        self.test_item.show()

        self.menu.append(self.test_item)
        self.menu.append(self.quit_item)

        # self.ind.set_label('lsyncd', 'LSYNCD')

    def main(self):
        self.logfile = open('/var/log/lsyncd/lsyncd.log', mode='rb')
        GLib.timeout_add(200, self.monitor_lsyncd)
        GLib.MainLoop().run()

    def quit(self, menuObj):
        GLib.MainLoop().quit()
        sys.exit(0)

    def open_config(test, test1):
        os.system('xdg-open "' + os.environ['HOME'] + '/.config/lsyncd/config.lua"')

    def monitor_lsyncd(self):
        lastLine = self.tail_log()
        self.update_indicator_index()

        logging.debug("Queue: " + self.lineType + " " + str(self.syncQueue) + " " + os.path.dirname(os.path.realpath(__file__)))

        # Found a match that a sync is happening
        if (self.lineType == 'FINISHED' and len(self.syncQueue) == 0):
            print("in case 1", file=sys.stderr)
            self.ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            self.ind.set_icon('greyspinner' + str(math.ceil(self.indicatorIconIndex / 4)))
        elif (self.lineType == 'FINISHED' and len(self.syncQueue) > 0):
            print("in case 2", file=sys.stderr)
            pass
        elif (self.lineType == 'SYNCING'):
            print("in case 3", file=sys.stderr)
            self.ind.set_icon('greenspinner' + str(math.ceil(self.indicatorIconIndex % 4) + 1))
            self.ind.set_status(AppIndicator.IndicatorStatus.ATTENTION)
        elif (self.lineType == 'LSYNCD TERMINATED'):
            print("in case 4", file=sys.stderr)
            self.ind.set_icon('redep')
            self.ind.set_status(AppIndicator.IndicatorStatus.ATTENTION)
        elif (self.lineType == 'ERROR'):
            print("in case 5", file=sys.stderr)
            self.ind.set_icon('redep')
            self.ind.set_status(AppIndicator.IndicatorStatus.ATTENTION)
        else:
            print("in case 6", file=sys.stderr)
            logging.warning("unknown something happening. Update some regular expressions")

        return True

    def update_indicator_index(self):
        if (self.indicatorIconIndex >= 16):
            self.indicatorIconIndex = 1
        else:
            self.indicatorIconIndex = self.indicatorIconIndex + 1

    def tail_log(self):
        # Keep track of the number of bytes has been written to the log file since the last loop
        amountToSeek = 0
        endOfFileByte = self.logfile.seek(0, 2)

        if (self.lastSeekPosition != endOfFileByte):
            amountToSeek = self.logfile.tell() - self.lastSeekPosition
            self.lastSeekPosition = self.logfile.tell()

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
            elif (self.lineType == 'ERROR'):
                self.syncQueue = []
            elif (self.lineType == 'STARTING SYNC'):
                self.syncQueue.append(self.lineType)

            line = self.logfile.readline().decode().rstrip()

        return lastLine

    def get_type_of_line(self, lastLine):
        if (re.search('exitcode: 0$', lastLine) or re.search('finished\.$', lastLine) or re.search('some files vanished', lastLine)):
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