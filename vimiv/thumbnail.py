#!/usr/bin/env python
# encoding: utf-8
""" Thumbnail part of vimiv """

import os
from gi import require_version
require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib
from vimiv.imageactions import thumbnails_create
from vimiv.helpers import scrolltypes


class Thumbnail(object):
    """ Thumbnail class for vimiv
        includes the iconview with the thumnbails and all actions that apply to
        it """

    def __init__(self, vimiv, settings):
        self.vimiv = vimiv
        general = settings["GENERAL"]

        # Settings
        self.toggled = False
        self.size = general["thumbsize"]
        self.cache = general["cache_thumbnails"]
        self.directory = os.path.join(self.vimiv.directory, "Thumbnails")
        self.timer_id = GLib.Timeout
        self.errorpos = 0
        self.pos = 0
        self.elements = []

        # Creates the Gtk elements necessary for thumbnail mode, fills them
        # and focuses the iconview
        # Create the liststore and iconview
        self.liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        self.iconview = Gtk.IconView.new()
        self.iconview.connect("item-activated", self.iconview_clicked)
        self.iconview.connect("key_press_event", self.vimiv.keyhandler.run,
                              "THUMBNAIL")
        self.iconview.set_model(self.liststore)
        self.columns = 0
        self.iconview.set_spacing(0)
        self.iconview.set_item_width(5)
        self.iconview.set_item_padding(10)
        self.iconview.set_pixbuf_column(0)
        self.iconview.set_border_width(1)
        self.iconview.set_markup_column(1)

    def iconview_clicked(self, w, count):
        """ Selects image when thumbnail was selected """
        # Move to the current position if the iconview is clicked
        self.toggle()
        count = count.get_indices()[0] + 1
        self.vimiv.keyhandler.vimiv.keyhandler.num_clear()
        for i in self.errorpos:
            if count > i:
                count += 1
        self.vimiv.keyhandler.vimiv.keyhandler.num_str = str(count)
        self.vimiv.image.move_pos()

    def toggle(self):
        """ Toggles thumbnail mode """
        if self.toggled:
            self.vimiv.image.viewport.remove(self.iconview)
            self.vimiv.image.viewport.add(self.vimiv.image.image)
            self.vimiv.image.update()
            self.vimiv.image.scrolled_win.grab_focus()
            self.toggled = False
        elif self.vimiv.paths:
            self.show()
            # Scroll to thumb
            self.timer_id = GLib.timeout_add(1, self.scroll_to_thumb)
            # Let the library keep focus
            if self.vimiv.library.focused:
                self.vimiv.library.treeview.grab_focus()
            # Manipulate bar is useless in thumbnail mode
            if self.vimiv.manipulate.toggled:
                self.vimiv.manipulate.toggle()
        else:
            self.vimiv.statusbar.vimiv.statusbar.err_message("No open image")
        # Update info for the current mode
        if not self.errorpos:
            self.vimiv.statusbar.update_info()

    def calculate_columns(self):
        """ Calculates how many columns fit into the current window and sets
            them for the iconview """
        window_width = self.vimiv.winsize[0]
        if self.vimiv.library.toggled:
            width = window_width - self.vimiv.library.width
        else:
            width = window_width
        self.columns = int(width / (self.size[0] + 30))
        self.iconview.set_columns(self.columns)

    def show(self):
        """ Shows thumbnail mode when called from toggle """
        # Clean liststore
        self.liststore.clear()
        # Create thumbnails
        self.elements, errtuple = thumbnails_create(self.vimiv.paths, self.size)
        self.errorpos = errtuple[0]
        if self.errorpos:
            failed_files = ", ".join(errtuple[1])
            self.vimiv.statusbar.err_message(
                "Thumbnail creation for %s failed" % (failed_files))

        # Add all thumbnails to the liststore
        for i, thumb in enumerate(self.elements):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(thumb)
            name = os.path.basename(thumb)
            name = name.split(".")[0]
            if self.vimiv.paths[i] in self.vimiv.mark.marked:
                name = name + " [*]"
            self.liststore.append([pixbuf, name])

        # Set columns
        self.calculate_columns()

        # Draw the icon view instead of the image
        self.vimiv.image.viewport.remove(self.vimiv.image.image)
        self.vimiv.image.viewport.add(self.iconview)

        # Show the window
        self.iconview.show()
        self.toggled = True

        # Focus the current immage
        self.iconview.grab_focus()
        self.pos = (self.vimiv.index) % len(self.vimiv.paths)
        for i in self.errorpos:
            if self.pos > i:
                self.pos -= 1
        curpath = Gtk.TreePath.new_from_string(str(self.pos))
        self.iconview.select_path(curpath)
        curthing = self.iconview.get_cells()[0]
        self.iconview.set_cursor(curpath, curthing, False)

        # Remove the files again if the thumbnails should not be cached
        if not self.cache:
            for thumb in self.elements:
                os.remove(thumb)

    def reload(self, thumb, index, reload_image=True):
        """ Reloads the thumbnail of manipulated images """
        for i in self.errorpos:
            if index > i:
                index -= 1
        liststore_iter = self.liststore.get_iter(index)
        self.liststore.remove(liststore_iter)
        try:
            if reload_image:
                self.elements = thumbnails_create([thumb], self.size)[0]
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.elements[index])

            name = os.path.basename(self.elements[index])
            name = name.split(".")[0]

            if thumb in self.vimiv.mark.marked:
                name = name + " [*]"
            self.liststore.insert(index, [pixbuf, name])
            path = Gtk.TreePath.new_from_string(str(self.pos))
            self.iconview.select_path(path)
            curthing = self.iconview.get_cells()[0]
            self.iconview.set_cursor(path, curthing, False)
        except:
            message = "Reload of manipulated thumbnails failed"
            self.vimiv.statusbar.err_message(message)

    def scroll_to_thumb(self):
        """ Function which scrolls to the currently selected thumbnail """
        # TODO
        scrollamount = int(self.pos / self.columns) * self.size[1]
        Gtk.Adjustment.set_step_increment(
            self.vimiv.image.viewport.get_vadjustment(), scrollamount)
        self.vimiv.image.scrolled_win.emit('scroll-child',
                                           Gtk.ScrollType.STEP_FORWARD, False)

    def move(self, direction):
        """ Select thumbnails correctly and scroll """
        # Get last element
        last = self.iconview.get_visible_range()[1]
        last = int(last.to_string())
        # Check for a user prefixed step
        if self.vimiv.keyhandler.num_str:
            step = int(self.vimiv.keyhandler.num_str)
        else:
            step = 1
        # Check for the specified thumbnail and handle exceptons
        if direction == "h":
            self.pos -= step
        elif direction == "k":
            self.pos -= self.columns * step
        elif direction == "l":
            self.pos += step
        else:
            self.pos += self.columns * step
        # Do not scroll to self.vimiv.paths that don't exist
        if self.pos < 0:
            self.pos = 0
        elif self.pos > last:
            self.pos = last
        # Move
        path = Gtk.TreePath.new_from_string(str(self.pos))
        self.iconview.select_path(path)
        curthing = self.iconview.get_cells()[0]
        self.iconview.set_cursor(path, curthing, False)
        # Actual scrolling TODO
        self.scroll(direction, step, self.pos)
        # Clear the user prefixed step
        self.vimiv.keyhandler.num_clear()

    def scroll(self, direction, step, target):
        """ Handles the actual scrolling """
        # TODO
        if step == 0:
            step += 1
        # Vertical
        if direction == "k" or direction == "j":
            Gtk.Adjustment.set_step_increment(
                self.vimiv.image.viewport.get_vadjustment(),
                (self.size[1] + 30) * step)
            self.vimiv.image.scrolled_win.emit('scroll-child',
                                               scrolltypes[direction][0], False)
        # Horizontal (tricky because one might reach a new column)
        else:
            start = target - step
            startcol = int(start / self.columns)
            endcol = int(target / self.columns)
            toscroll = endcol - startcol
            Gtk.Adjustment.set_step_increment(
                self.vimiv.image.viewport.get_vadjustment(),
                (self.size[1] + 30) * toscroll)
            self.vimiv.image.scrolled_win.emit('scroll-child',
                                               scrolltypes[direction][0], False)