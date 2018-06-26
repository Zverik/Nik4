# -*- coding: utf-8 -*-

import unittest
import shlex

from nik4.nik4_image import Nik4Image


WEB_MERC = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over'

class MapSettingsTestCase(unittest.TestCase):

    def setUp(self):
        self.parser = Nik4Image.get_argument_parser()

    def get_args_str(self):
        return 'style.xml out.png'

    def get_settings(self, test_str):
        test_str += ' ' + self.get_args_str()
        options = self.parser.parse_args(shlex.split(test_str))
        return Nik4Image.setup_options(options)


    def test_zoom_and_bbox(self):
        settings = self.get_settings('-z 14 -b 8.01 49.09 8.05 49.12')
        self.assertFalse(settings.need_cairo)
        self.assertAlmostEqual(settings.bbox[0], 891669.1212541225)
        self.assertAlmostEqual(settings.bbox[1], 6290146.33132722)
        self.assertAlmostEqual(settings.bbox[2], 896121.9008858531)
        self.assertAlmostEqual(settings.bbox[3], 6295247.466433874)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertAlmostEqual(settings.scale, 9.554620465197562)
        self.assertIsNone(settings.size)
        self.assertEqual(settings.scale_factor, 1)
        self.assertEqual(settings.fmt, 'png')

    def test_center_zoom_pixel_dimensions(self):
        settings = self.get_settings('-c 8.0327 49.0748 -z 14 -x 400 600')
        self.assertFalse(settings.need_cairo)
        self.assertAlmostEqual(settings.bbox[0], 892285.14960208)
        self.assertAlmostEqual(settings.bbox[1], 6284696.54652795)
        self.assertAlmostEqual(settings.bbox[2], 896106.99778817)
        self.assertAlmostEqual(settings.bbox[3], 6290429.31880707)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertAlmostEqual(settings.scale, 9.5546204652)
        self.assertEqual(settings.size, [400, 600])
        self.assertEqual(settings.scale_factor, 1)
        self.assertEqual(settings.fmt, 'png')
