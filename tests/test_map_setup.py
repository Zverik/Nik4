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
        settings = Nik4Image(options)
        settings.setup_options()
        return settings


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

    def test_only_center_scale(self):
        settings = self.get_settings('-c 8.0327 49.0748 --scale 25000')
        self.assertIsNone(settings.bbox)

    def test_only_center_scale_ppi(self):
        settings = self.get_settings('-c 8.0327 49.0748 --scale 25000 --ppi 90')
        self.assertIsNone(settings.bbox)

    def test_bbox_scale_ppi(self):
        settings = self.get_settings('-b 8.0327 49.0748 8.0828 49.1049 --scale 25000 --ppi 90')
        self.assertFalse(settings.need_cairo)
        self.assertAlmostEqual(settings.bbox[0], 894196.07369513)
        self.assertAlmostEqual(settings.bbox[1], 6287562.93266751)
        self.assertAlmostEqual(settings.bbox[2], 899773.18018387)
        self.assertAlmostEqual(settings.bbox[3], 6292679.50961837)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertAlmostEqual(settings.scale, 10.7722048292)
        # size of the image cannot be checked here because it is calculated later
        #self.assertEqual(settings.size, [518, 475])
        self.assertAlmostEqual(settings.scale_factor, 0.992282249173)
        self.assertEqual(settings.fmt, 'png')

    def test_center_scale_ppi_pixels(self):
        settings = self.get_settings('-c 8.0327 49.0748 --scale 25000 --ppi 90 -x 400 600')
        self.assertAlmostEqual(settings.bbox[0], 892042.28552930)
        self.assertAlmostEqual(settings.bbox[1], 6284332.25041877)
        self.assertAlmostEqual(settings.bbox[2], 896349.86186095)
        self.assertAlmostEqual(settings.bbox[3], 6290793.61491624)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertAlmostEqual(settings.scale, 10.7689408291)
        self.assertEqual(settings.size, [400, 600])
        self.assertAlmostEqual(settings.scale_factor, 0.992282249173)

    def test_center_scale_ppi_mm(self):
        settings = self.get_settings('-c 8.0327 49.0748 --scale 25000 --ppi 90 -d 400 600')
        self.assertAlmostEqual(settings.bbox[0], 886566.27911769)
        self.assertAlmostEqual(settings.bbox[1], 6276115.54856614)
        self.assertAlmostEqual(settings.bbox[2], 901825.86827256)
        self.assertAlmostEqual(settings.bbox[3], 6299010.31676887)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertAlmostEqual(settings.scale, 10.7689408291)
        self.assertEqual(settings.size, [1417, 2126])
        self.assertAlmostEqual(settings.scale_factor, 0.992282249173)

    def test_center_scale_300ppi_mm(self):
        settings = self.get_settings('-c 8.0327 49.0748 --scale 25000 --ppi 300 -d 400 600')
        self.assertAlmostEqual(settings.bbox[0], 886565.20222361)
        self.assertAlmostEqual(settings.bbox[1], 6276115.01011910)
        self.assertAlmostEqual(settings.bbox[2], 901826.94516665)
        self.assertAlmostEqual(settings.bbox[3], 6299010.85521591)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertAlmostEqual(settings.scale, 3.23068224874)
        self.assertEqual(settings.size, [4724, 7087])
        self.assertAlmostEqual(settings.scale_factor, 3.30760749724)

    def test_bbox_pixels(self):
        settings = self.get_settings('-b 8.0327 49.0748 8.0828 49.1049 -x 400 600')
        self.assertAlmostEqual(settings.bbox[0], 894196.07369513)
        self.assertAlmostEqual(settings.bbox[1], 6287562.93266751)
        self.assertAlmostEqual(settings.bbox[2], 899773.18018387)
        self.assertAlmostEqual(settings.bbox[3], 6292679.50961837)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertIsNone(settings.scale)
        self.assertEqual(settings.size, [400, 600])
        self.assertEqual(settings.scale_factor, 1)

    def test_bbox_pixels_sf3(self):
        settings = self.get_settings('-b 8.0327 49.0748 8.0828 49.1049 -x 400 600 --factor 3')
        self.assertAlmostEqual(settings.bbox[0], 894196.07369513)
        self.assertAlmostEqual(settings.bbox[1], 6287562.93266751)
        self.assertAlmostEqual(settings.bbox[2], 899773.18018387)
        self.assertAlmostEqual(settings.bbox[3], 6292679.50961837)
        self.assertIsNone(settings.scale)
        self.assertEqual(settings.size, [400, 600])
        self.assertEqual(settings.scale_factor, 3.0)

    def test_bbox_pixels_300ppi(self):
        settings = self.get_settings('-b 8.0327 49.0748 8.0828 49.1049 -x 400 600 --ppi 300')
        self.assertFalse(settings.need_cairo)
        self.assertAlmostEqual(settings.bbox[0], 894196.07369513)
        self.assertAlmostEqual(settings.bbox[1], 6287562.93266751)
        self.assertAlmostEqual(settings.bbox[2], 899773.18018387)
        self.assertAlmostEqual(settings.bbox[3], 6292679.50961837)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertIsNone(settings.scale)
        self.assertEqual(settings.size, [400, 600])
        self.assertAlmostEqual(settings.scale_factor, 3.30760749724)
