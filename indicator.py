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

    def menu_setup(self):
        self.menu = Gtk.Menu()
        self.quit_item = Gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()
        self.menu.append(self.quit_item)
        # self.ind.set_label('lsyncd', 'LSYNCD')

    def main(self):
        self.logfile = open('/var/log/lsyncd/lsyncd.log', mode='rb')
        GLib.timeout_add(250, self.monitor_lsyncd)
        GLib.MainLoop().run()

    def quit(self, menuObj):
        GLib.MainLoop().quit()
        sys.exit(0)

    def monitor_lsyncd(self):
        lastLine = self.tail3()

        # Found a match that a sync is happening
        if (re.search('exitcode: 0$', lastLine) or re.search('finished\.$', lastLine)):
            self.ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            self.ind.set_icon('bluespinner')
            self.ind.set_label('idle', 'LSYNCD')
        elif (re.search('/$', lastLine) or re.search('[\*\w]\.\w+$', lastLine)):
            self.ind.set_icon('greenspinner')
            self.ind.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            self.ind.set_label('sync', 'LSYNCD')
        elif (re.search('TERM signal, fading ---', lastLine)):
            self.ind.set_icon('redep')
            self.ind.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            self.ind.set_label('no lsyncd', 'LSYNCD')
        elif (re.search('error|Error', lastLine)):
            self.ind.set_icon('redep')
            self.ind.set_status(AppIndicator.IndicatorStatus.ATTENTION)
            self.ind.set_label('error', 'LSYNCD')
        else:
            print ("unknown something happening. Update some regular expressions")

        return True

    def tail3(self, lines=1):
        f = self.logfile
        f.seek(0, 2)
        f.seek(-200, 1)
        line = f.readline().decode()
        lastLine = line
        while line != '':
            line = f.readline().decode()
            if (line == ''):
                break
            else:
                lastLine = line

        return lastLine.rstrip()

if __name__ == "__main__":
    indicator = LsyncdIndicator()
    indicator.main()