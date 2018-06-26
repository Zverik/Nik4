# -*- coding: utf-8 -*-

import unittest
import shlex

from nik4.nik4_image import Nik4Image

class MapSettingsTestCase(unittest.TestCase):
    def setUp(self):
        self.parser = Nik4Image.get_argument_parser()

    def get_args_str(self):
        return 'style.xml out.png'

    def test_zoom_and_bbox(self):
        test_str = '-z 14 -b 8.01 49.09 8.05 49.12 ' + self.get_args_str()
        options = self.parser.parse_args(shlex.split(test_str))
        settings = Nik4Image.setup_options(options)
        self.assertAlmostEqual(settings.scale, 9.55462046)
        self.assertFalse(settings.need_cairo)
        self.assertAlmostEqual(settings.bbox[0], 891669.1212541225)
        self.assertAlmostEqual(settings.bbox[1], 6290146.33132722)
        self.assertAlmostEqual(settings.bbox[2], 896121.9008858531)
        self.assertAlmostEqual(settings.bbox[3], 6295247.466433874)
        self.assertEqual(settings.proj_target.expanded(), '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over')
        self.assertAlmostEqual(settings.scale, 9.554620465197562)
        self.assertIsNone(settings.size)
        self.assertEqual(settings.scale_factor, 1)
        self.assertEqual(settings.fmt, 'png')
