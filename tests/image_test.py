# vim: ft=python fileencoding=utf-8 sw=4 et sts=4
"""Test image mode for vimiv's testsuite."""

from unittest import main

from gi import require_version
require_version("Gtk", "3.0")
from gi.repository import Gtk

from vimiv_testcase import VimivTestCase, refresh_gui


class ImageTest(VimivTestCase):
    """Image mode Test."""

    @classmethod
    def setUpClass(cls):
        cls.init_test(cls, ["vimiv/testimages/arch_001.jpg"])
        cls.image = cls.vimiv["image"]

    def test_zoom_percent(self):
        """Test getting the fitting image zoom."""
        # Panorama image
        width = 1920
        im_width = self.image.imsize[0]
        perc = self.image.get_zoom_percent_to_fit()
        self.assertEqual(im_width / width, perc)

    def test_zooming(self):
        """Zooming of images."""
        width = 1920
        # Zoom in
        perc_before = self.image.zoom_percent
        self.image.zoom_delta()
        self.assertEqual(self.image.zoom_percent, perc_before * 1.25)
        # Zoom out should go back to same level
        self.image.zoom_delta(zoom_in=False)
        self.assertEqual(self.image.zoom_percent, perc_before)
        # Zoom in with a step
        self.image.zoom_delta(step=2)
        self.assertEqual(self.image.zoom_percent, perc_before * 1.5)
        # zoom out by eventhandler to same level
        self.vimiv["eventhandler"].num_str = "2"
        self.image.zoom_delta(zoom_in=False)
        self.assertEqual(self.image.zoom_percent, perc_before)
        # Zoom to a size representing half the image size
        self.image.zoom_to(0.5)
        self.assertEqual(self.image.zoom_percent, 0.5)
        pixbuf = self.image.image.get_pixbuf()
        self.assertEqual(width * 0.5, pixbuf.get_width())
        # Zoom by eventhandler
        self.vimiv["eventhandler"].num_str = "03"
        self.image.zoom_to(0)
        self.assertEqual(self.image.zoom_percent, 0.3)
        pixbuf = self.image.image.get_pixbuf()
        self.assertEqual(width * 0.3, pixbuf.get_width())
        # Zoom back to fit
        self.image.zoom_to(0)
        self.assertEqual(self.image.zoom_percent,
                         self.image.get_zoom_percent_to_fit())
        pixbuf = self.image.image.get_pixbuf()
        self.assertEqual(width * self.image.get_zoom_percent_to_fit(),
                         pixbuf.get_width())
        # Unreasonable zoom
        self.image.zoom_to(1000)
        self.check_statusbar("WARNING: Image cannot be zoomed this far")
        pixbuf = self.image.image.get_pixbuf()
        self.assertEqual(width * self.image.get_zoom_percent_to_fit(),
                         pixbuf.get_width())

    def test_zoom_from_commandline(self):
        """Test zooming from command line."""
        # Zoom in
        expected_zoom = self.image.zoom_percent * 1.25
        self.run_command("zoom_in")
        self.assertEqual(expected_zoom, self.image.zoom_percent)
        # Zoom out with step
        expected_zoom = self.image.zoom_percent / 1.5
        self.run_command("zoom_out 2")
        self.assertEqual(expected_zoom, self.image.zoom_percent)
        # Zoom with invalid argument
        self.run_command("zoom_out value")
        self.check_statusbar("ERROR: Argument for zoom must be of type float")
        # Zoom to fit
        self.run_command("fit")
        self.assertEqual(self.image.zoom_percent,
                         self.image.get_zoom_percent_to_fit())
        # Fit horizontally
        self.run_command("fiz_horiz")
        self.assertEqual(self.image.zoom_percent,
                         self.image.get_zoom_percent_to_fit())
        # Fit vertically
        self.run_command("fit_vert")
        self.assertEqual(self.image.zoom_percent,
                         self.image.get_zoom_percent_to_fit(3))
        # Zoom_to 0.5
        self.run_command("zoom_to 05")
        self.assertEqual(self.image.zoom_percent, 0.5)
        # Zoom_to with invalid argument
        self.run_command("zoom_to value")
        self.check_statusbar("ERROR: Argument for zoom must be of type float")

    def test_move(self):
        """Move from image to image."""
        self.assertEqual(0, self.vimiv.index)
        self.image.move_index()
        self.assertEqual(1, self.vimiv.index)
        self.image.move_index(forward=False)
        self.assertEqual(0, self.vimiv.index)
        self.image.move_index(delta=2)
        self.assertEqual(2, self.vimiv.index)
        self.image.move_pos()
        self.assertEqual(len(self.vimiv.paths) - 1, self.vimiv.index)
        self.image.move_pos(forward=False)
        self.assertEqual(0, self.vimiv.index)

    def test_toggles(self):
        """Toggle image.py settings."""
        # Rescale svg
        before = self.image.rescale_svg
        self.image.toggle_rescale_svg()
        self.assertFalse(before == self.image.rescale_svg)
        self.image.toggle_rescale_svg()
        self.assertTrue(before == self.image.rescale_svg)
        # Overzoom
        before = self.image.overzoom
        self.image.toggle_overzoom()
        self.assertFalse(before == self.image.overzoom)
        self.image.toggle_overzoom()
        self.assertTrue(before == self.image.overzoom)
        # Animations should be tested in animation_test.py

    def test_check_for_edit(self):
        """Check if an image was edited."""
        self.assertEqual(0, self.image.check_for_edit(False))
        self.vimiv["manipulate"].manipulations = {"bri": 10, "con": 0, "sha": 0}
        self.assertEqual(1, self.image.check_for_edit(False))
        self.assertEqual(0, self.image.check_for_edit(True))

    def test_auto_rezoom_on_changes(self):
        """Automatically rezoom the image when different widgets are shown."""
        # Definitely show statusbar
        if self.vimiv["statusbar"].hidden:
            self.vimiv["statusbar"].toggle()
        # Zoom to fit vertically so something happens
        self.image.zoom_to(0, 3)
        before = self.image.zoom_percent
        # Hide statusbar -> larger image
        self.vimiv["statusbar"].toggle()
        after = self.image.zoom_percent
        self.assertGreater(after, before)
        # Show statusbar -> image back to size before
        self.vimiv["statusbar"].toggle()
        after = self.image.zoom_percent
        self.assertEqual(after, before)
        # Zoom to fit horizontally so something happens
        self.image.zoom_to(0, 2)
        before = self.image.zoom_percent
        # Show library -> smaller image
        self.vimiv["library"].toggle()
        after = self.image.zoom_percent
        self.assertLess(after, before)
        # Hide library again -> image back to size before
        self.vimiv["library"].toggle()
        after = self.image.zoom_percent
        self.assertEqual(after, before)

    def test_scroll(self):
        """Scroll an image."""
        def there_and_back(there, back):
            """Scroll in direction and back to the beginning.

            Args:
                there: Direction to scroll in.
                back: Direction to scroll back in.
            Return:
                Position after scrolling.
            """
            if there in "lL":
                adj = Gtk.Scrollable.get_hadjustment(self.image.viewport)
            else:
                adj = Gtk.Scrollable.get_vadjustment(self.image.viewport)
            self.image.scroll(there)
            new_pos = adj.get_value()
            self.assertGreater(adj.get_value(), 0)
            self.image.scroll(back)
            self.assertFalse(adj.get_value())
            return new_pos
        refresh_gui()
        # First zoom so something can happen
        self.image.zoom_to(1)
        refresh_gui()
        # Adjustments should be at 0
        h_adj = Gtk.Scrollable.get_hadjustment(self.image.viewport)
        v_adj = Gtk.Scrollable.get_vadjustment(self.image.viewport)
        self.assertFalse(h_adj.get_value())
        self.assertFalse(v_adj.get_value())
        # Right and back left
        there_and_back("l", "h")
        # Down and back up
        there_and_back("j", "k")
        # Far right and back
        right_end = there_and_back("L", "H")
        self.assertEqual(
            right_end,
            h_adj.get_upper() - h_adj.get_lower() - self.image.imsize[0])
        # Bottom and back
        # off by 1?
        bottom = there_and_back("J", "K")
        self.assertEqual(
            bottom,
            v_adj.get_upper() - v_adj.get_lower() - self.image.imsize[1])
        # Center
        self.image.center_window()
        h_adj = Gtk.Scrollable.get_hadjustment(self.image.viewport)
        v_adj = Gtk.Scrollable.get_vadjustment(self.image.viewport)
        h_middle = \
            (h_adj.get_upper() - h_adj.get_lower() - self.image.imsize[0]) / 2
        v_middle = \
            (v_adj.get_upper() - v_adj.get_lower() - self.image.imsize[1]) / 2
        self.assertEqual(h_adj.get_value(), h_middle)
        self.assertEqual(v_adj.get_value(), v_middle)


if __name__ == "__main__":
    main()
