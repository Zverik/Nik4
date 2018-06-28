# -*- coding: utf-8 -*-

import argparse
import logging
import mapnik
import math
import re
from nik4.paper_size import get_paper_size


VERSION = '1.7'
EPSG_4326 = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
EPSG_3857 = ('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 ' +
             '+k=1.0 +units=m +nadgrids=@null +no_defs +over')
PROJ_LONLAT = mapnik.Projection(EPSG_4326)
PROJ_WEB_MERC = mapnik.Projection(EPSG_3857)
TRANSFORM_LONLAT_WEBMERC = mapnik.ProjTransform(PROJ_LONLAT, PROJ_WEB_MERC)

class Nik4Image:

    def __init__(self, options, has_cairo):
        self.options = options
        self.has_cairo = has_cairo
        self.need_cairo = False
        self.fmt = None
        self.ppmm = None
        self.scale = None
        self.fix_scale = False
        self.scale_factor = None
        self.size = None
        self.bbox = None
        self.transform = None
        self.proj_target = None
        self.rotate = None


    def _parse_url(self, url, options):
        """Parse map URL into options map"""
        lat = None
        lon = None
        zoom = None
        m = re.search(r'[#/=]([0-9]{1,2})/(-?[0-9]{1,2}\.[0-9]+)/(-?[0-9]{1,3}\.[0-9]+)', url)
        if m:
            zoom = int(m.group(1))
            lat = float(m.group(2))
            lon = float(m.group(3))
        else:
            m = re.search(r'lat=(-[0-9]{1,2}\.[0-9]+)', url, flags=re.IGNORECASE)
            if m:
                lat = float(m.group(1))
            m = re.search(r'lon=(-[0-9]{1,3}\.[0-9]+)', url, flags=re.IGNORECASE)
            if m:
                lon = float(m.group(1))
            m = re.search(r'zoom=([0-9]{1,2})', url, flags=re.IGNORECASE)
            if m:
                zoom = int(m.group(1))
        if zoom and not options.zoom:
            self.options.zoom = zoom
        if lat and lon and not self.options.center:
            self.options.center = [lon, lat]
        if (not self.options.size and not self.options.size_px and not self.options.paper
                and not self.options.fit and not self.options.bbox):
            self.options.size_px = [1280, 1024]

    def _set_format(self):
        # format should not be empty
        if self.options.fmt:
            self.fmt = self.options.fmt.lower()
        elif '.' in self.options.output:
            self.fmt = self.options.output.split('.')[-1].lower()
        else:
            self.fmt = 'png256'

        self.need_cairo = self.fmt in ['svg', 'pdf']

    def _set_ppm_and_scale_factor(self):
        """
        Set properties ppm and scale_factor.
        """
        # ppi and scale factor are the same thing
        if self.options.ppi:
            self.ppmm = self.options.ppi / 25.4
            self.scale_factor = self.options.ppi / 90.7
        else:
            self.scale_factor = self.options.factor
            self.ppmm = 90.7 / 25.4 * self.scale_factor

        # svg / pdf can be scaled only in cairo mode
        if self.scale_factor != 1 and self.need_cairo and not self.has_cairo:
            logging.error('Warning: install pycairo for using --factor or --ppi')
            self.scale_factor = 1
            self.ppmm = 90.7 / 25.4

    def _set_projections_and_transform(self):
        if self.options.projection.isdigit():
            self.proj_target = mapnik.Projection('+init=epsg:{}'.format(self.options.projection))
        else:
            self.proj_target = mapnik.Projection(self.options.projection)
        self.transform = mapnik.ProjTransform(PROJ_LONLAT, self.proj_target)

    def _set_bbox_with_center_scale_and_size(self):
        # We don't know over which latitude range the bounding box spans, so we
        # first do everything in Web Mercator.
        center = TRANSFORM_LONLAT_WEBMERC.forward(mapnik.Coord(*self.options.center))
        w = self.size[0] * self.scale / 2
        h = self.size[1] * self.scale / 2
        bbox_web_merc = mapnik.Box2d(center.x-w, center.y-h, center.x+w, center.y+h)
        self.bbox = TRANSFORM_LONLAT_WEBMERC.backward(bbox_web_merc)
        self.bbox = self.transform.forward(self.bbox)
        # now correct the scale
        self.correct_scale(bbox_web_merc)
        center = self.transform.forward(mapnik.Coord(*self.options.center))
        w = self.size[0] * self.scale / 2
        h = self.size[1] * self.scale / 2
        self.bbox = mapnik.Box2d(center.x-w, center.y-h, center.x+w, center.y+h)

    def setup_options(self):
        dim_mm = None
        self.rotate = not self.options.norotate

        if (self.options.ozi and self.options.projection.lower() != 'epsg:3857'
                and self.options.projection != EPSG_3857):
            raise Exception('Ozi map file output is only supported for Web Mercator (EPSG:3857). ' +
                            'Please remove --projection.')

        self._set_format()

        if self.options.url:
            self._parse_url(self.options.url, self.options)

        # output projection
        self._set_projections_and_transform()

        # get image size in millimeters
        if self.options.paper:
            portrait = False
            if self.options.paper[0] == '-':
                portrait = True
                self.rotate = False
                self.options.paper = self.options.paper[1:]
            elif self.options.paper[0] == '+':
                self.rotate = False
                self.options.paper = self.options.paper[1:]
            else:
                self.rotate = True
            dim_mm = get_paper_size(self.options.paper.lower())
            if not dim_mm:
                raise Exception('Incorrect paper format: ' + self.options.paper)
            if portrait:
                dim_mm = [dim_mm[1], dim_mm[0]]
        elif self.options.size:
            dim_mm = self.options.size
        if dim_mm and self.options.margin:
            dim_mm[0] = max(0, dim_mm[0] - self.options.margin * 2)
            dim_mm[1] = max(0, dim_mm[1] - self.options.margin * 2)

        self._set_ppm_and_scale_factor()

        # convert physical size to pixels
        if self.options.size_px:
            self.size = self.options.size_px
        elif dim_mm:
            self.size = [int(round(dim_mm[0] * self.ppmm)), int(round(dim_mm[1] * self.ppmm))]

        if self.size and self.size[0] + self.size[1] <= 0:
            raise Exception('Both dimensions are less or equal to zero')

        if self.options.bbox:
            self.bbox = self.options.bbox

        # scale can be specified with zoom or with 1:NNN scale
        if self.options.zoom:
            self.scale = 2 * 3.14159 * 6378137 / 2 ** (self.options.zoom + 8) / self.scale_factor
        elif self.options.scale:
            self.scale = self.options.scale * 0.00028 / self.scale_factor
            # Now we have to divide by cos(lat), but we might not know latitude at this point
            # TODO: division should only happen for EPSG:3857 or not at all
            if self.options.center:
                self.scale = self.scale / math.cos(math.radians(self.options.center[1]))
            elif self.options.bbox:
                self.scale = self.scale / math.cos(math.radians((self.options.bbox[3] + self.options.bbox[1]) / 2))
            else:
                self.fix_scale = True

        # all calculations are in EPSG:3857 projection (it's easier)
        if self.bbox:
            self.bbox = self.transform.forward(mapnik.Box2d(*self.bbox))
            bbox_web_merc = TRANSFORM_LONLAT_WEBMERC.forward(mapnik.Box2d(*(self.options.bbox)))
            if self.scale:
                self.correct_scale(bbox_web_merc)

        # calculate bbox through center, zoom and target size
        if not self.bbox and self.options.center and self.size and self.size[0] > 0 and self.size[1] > 0 and self.scale:
            self._set_bbox_with_center_scale_and_size()

    def correct_scale(self, bbox_web_merc):
        # correct scale if output projection is not EPSG:3857
        x_dist_merc = bbox_web_merc.maxx - bbox_web_merc.minx
        x_dist_target = self.bbox.maxx - self.bbox.minx
        self.scale = self.scale * (x_dist_target / x_dist_merc)

    @staticmethod
    def get_argument_parser():
        parser = argparse.ArgumentParser(
            description='Nik4 {}: Tile-aware mapnik image renderer'.format(VERSION))
        parser.add_argument('--version', action='version', version='Nik4 {}'.format(VERSION))
        parser.add_argument('-z', '--zoom', type=float, help='Target zoom level')
        parser.add_argument('-p', '--ppi', '--dpi', type=float,
                            help='Pixels per inch (alternative to scale)')
        parser.add_argument('--factor', type=float, default=1,
                            help='Scale factor (affects ppi, default=1)')
        parser.add_argument('-s', '--scale', type=float,
                            help='Scale as in 1:100000 (specifying ppi is recommended)')
        parser.add_argument('-b', '--bbox', nargs=4, type=float,
                            metavar=('Xmin', 'Ymin', 'Xmax', 'Ymax'), help='Bounding box')
        parser.add_argument('-a', '--paper',
                            help='Paper format: -a +4 for landscape A4, -a -4 for portrait A4, ' +
                            '-a letter for autorotated US Letter')
        parser.add_argument('-d', '--size', nargs=2, metavar=('W', 'H'), type=int,
                            help='Target dimensions in mm (one 0 allowed)')
        parser.add_argument('-x', '--size-px', nargs=2, metavar=('W', 'H'), type=int,
                            help='Target dimensions in pixels (one 0 allowed)')
        parser.add_argument('--norotate', action='store_true', default=False,
                            help='Do not swap width and height for bbox')
        parser.add_argument('-m', '--margin', type=int,
                            help='Amount in mm to reduce paper size')
        parser.add_argument('-c', '--center', nargs=2, metavar=('X', 'Y'), type=float,
                            help='Center of an image')

        parser.add_argument('--fit', help='Fit layers in the map, comma-separated')
        parser.add_argument('--padding', type=int, default=5,
                            help='Margin for layers in --fit (default=5), mm')
        parser.add_argument('--layers', help='Map layers to render, comma-separated')
        parser.add_argument('--add-layers', help='Map layers to include, comma-separated')
        parser.add_argument('--hide-layers', help='Map layers to hide, comma-separated')

        parser.add_argument('-P', '--projection', default=EPSG_3857,
                            help='EPSG code as 1234 (without prefix "EPSG:" or Proj4 string')

        parser.add_argument('--url', help='URL of a map to center on')
        parser.add_argument('--ozi', type=argparse.FileType('w'), help='Generate ozi map file')
        parser.add_argument('--wld', type=argparse.FileType('w'), help='Generate world file')
        parser.add_argument('-t', '--tiles', default='1',
                            help='Write N×N (--tiles N) or N×M (--tiles NxM) tiles, then join using imagemagick')
        parser.add_argument('--just-tiles', action='store_true', default=False,
                            help='Do not join tiles, instead write ozi/wld file for each')
        parser.add_argument('-v', '--debug', action='store_true', default=False,
                            help='Display calculated values')
        parser.add_argument('-f', '--format', dest='fmt',
                            help='Target file format (by default looks at extension)')
        parser.add_argument('--base',
                            help='Base path for style file, in case it\'s piped to stdin')
        parser.add_argument('--vars', nargs='*',
                            help='List of variables (name=value) to substitute in ' +
                            'style file (use ${name:default})')
        parser.add_argument('--fonts', nargs='*',
                            help='List of full path to directories containing fonts')
        parser.add_argument('style', help='Style file for mapnik')
        parser.add_argument('output', help='Resulting image file')
        return parser
