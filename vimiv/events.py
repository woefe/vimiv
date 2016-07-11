#!/usr/bin/env python
# encoding: utf-8
""" Handles events for vimiv, e.g. fullscreen, resize, keypress """

from gi import require_version
require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib
from vimiv.helpers import scrolltypes
from vimiv.parser import parse_keys

class Window(object):
    """ Window class for vimiv
        handles fullscreen and resize """

    def __init__(self, vimiv, settings):
        self.vimiv = vimiv
        self.fullscreen = False
        self.vimiv.connect_object('window-state-event',
                                   Window.on_window_state_change,
                                   self)
        self.last_focused = ""

        # The configruations from vimivrc
        general = settings["GENERAL"]

        # General
        start_fullscreen = general["start_fullscreen"]
        if start_fullscreen:
            self.toggle_fullscreen()

        # Connect
        self.vimiv.connect("check-resize", self.auto_resize)

    def on_window_state_change(self, event):
        self.fullscreen = bool(Gdk.WindowState.FULLSCREEN
                               & event.new_window_state)

    def toggle_fullscreen(self):
        """ Toggles fullscreen """
        if self.fullscreen:
            self.vimiv.unfullscreen()
        else:
            self.vimiv.fullscreen()
        # Adjust the image if necessary
        if self.vimiv.paths:
            if self.vimiv.user_zoomed:
                self.vimiv.update_image()
            else:
                self.vimiv.zoom_to(0)

    def auto_resize(self, w):
        """ Automatically resize image when window is resized """
        if self.vimiv.get_size() != self.vimiv.winsize:
            self.vimiv.winsize = self.vimiv.get_size()
            if self.vimiv.paths and not self.vimiv.image.user_zoomed:
                self.vimiv.image.zoom_to(0)
            elif not self.vimiv.paths and self.vimiv.library.expand:
                self.vimiv.library.grid.set_size_request(self.vimiv.winsize[0],
                                                         10)
            self.vimiv.commandline.info.set_max_width_chars(self.vimiv.winsize[0]/16)



class KeyHandler(object):
    """ Handles key press for vimiv invoking the correct commands """

    def __init__(self, vimiv, settings):
        # Add events to vimiv
        self.vimiv = vimiv
        self.vimiv.add_events(Gdk.EventMask.KEY_PRESS_MASK |
                              Gdk.EventMask.POINTER_MOTION_MASK)
        # Settings
        self.num_str = ""
        self.keys = parse_keys()

    def run(self, widget, event, window):
        """ Runs the correct function per keypress """
        keyval = event.keyval
        keyname = Gdk.keyval_name(keyval)
        shiftkeys = ["space", "Return", "Tab", "Escape", "BackSpace",
                     "Up", "Down", "Left", "Right"]
        # Check for Control (^), Mod1 (Alt) or Shift
        if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            keyname = "^" + keyname
        if event.get_state() & Gdk.ModifierType.MOD1_MASK:
            keyname = "Alt+" + keyname
        # Shift+ for all letters and for keys that don't support it
        if (event.get_state() & Gdk.ModifierType.SHIFT_MASK and
                (len(keyname) < 2 or keyname in shiftkeys)):
            keyname = "Shift+" + keyname.lower()
        try:  # Numbers for the num_str
            if window == "COMMAND":
                raise ValueError
            int(keyname)
            self.num_append(keyname)
            return True
        except:
            try:
                # Get the relevant keybindings for the window from the various
                # sections in the keys.conf file
                keys = self.keys[window]

                # Get the command to which the pressed key is bound
                func = keys[keyname]
                if "set " in func:
                    conf_args = []
                else:
                    func = func.split()
                    conf_args = func[1:]
                    func = func[0]
                # From functions dictionary get the actual vimiv command
                func = self.vimiv.functions[func]
                args = func[1:]
                args.extend(conf_args)
                func = func[0]
                func(*args)
                return True  # Deactivates default bindings
            except:
                return False

    def scroll(self, direction):
        """ Scroll the correct object """
        if self.vimiv.thumbnail.toggled:
            self.vimiv.thumbnail.move(direction)
        else:
            self.vimiv.image.scrolled_win.emit('scroll-child',
                                               scrolltypes[direction][0],
                                               scrolltypes[direction][1])
        return True  # Deactivates default bindings (here for Arrows)

    def num_append(self, num):
        """ Adds a new char to the num_str """
        self.num_str += num
        # RISKY
        GLib.timeout_add_seconds(1, self.num_clear)
        self.vimiv.statusbar.update_info()

    def num_clear(self):
        """ Clears the num_str """
        self.num_str = ""
        self.vimiv.statusbar.update_info()
