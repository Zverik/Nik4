# -*- coding: utf-8 -*-

import argparse
import math
import mapnik


VERSION = '1.7'
EPSG_4326 = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
EPSG_3857 = ('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 ' +
             '+k=1.0 +units=m +nadgrids=@null +no_defs +over')
PROJ_LONLAT = mapnik.Projection(EPSG_4326)
PROJ_WEB_MERC = mapnik.Projection(EPSG_3857)
TRANSFORM_LONLAT_WEBMERC = mapnik.ProjTransform(PROJ_LONLAT, PROJ_WEB_MERC)

class Nik4Image:

    def __init__(self):
        self.need_cairo = False
        self.fmt = None
        self.scale = None
        self.scale_factor = None
        self.size = None
        self.bbox = None
        self.transform = None
        self.proj_target = None
        self.rotate = None

    @staticmethod
    def setup_options(options):
        settings = Nik4Image()
        dim_mm = None
        settings.rotate = not options.norotate

        if (options.ozi and options.projection.lower() != 'epsg:3857'
                and options.projection != EPSG_3857):
            raise Exception('Ozi map file output is only supported for Web Mercator (EPSG:3857). ' +
                            'Please remove --projection.')

        if options.url:
            parse_url(options.url, options)

        # format should not be empty
        if options.fmt:
            settings.fmt = options.fmt.lower()
        elif '.' in options.output:
            settings.fmt = options.output.split('.')[-1].lower()
        else:
            settings.fmt = 'png256'

        settings.need_cairo = settings.fmt in ['svg', 'pdf']

        # output projection
        if options.projection.isdigit():
            settings.proj_target = mapnik.Projection('+init=epsg:{}'.format(options.projection))
        else:
            settings.proj_target = mapnik.Projection(options.projection)
        settings.transform = mapnik.ProjTransform(PROJ_LONLAT, settings.proj_target)

        # get image size in millimeters
        if options.paper:
            portrait = False
            if options.paper[0] == '-':
                portrait = True
                settings.rotate = False
                options.paper = options.paper[1:]
            elif options.paper[0] == '+':
                settings.rotate = False
                options.paper = options.paper[1:]
            else:
                settings.rotate = True
            dim_mm = get_paper_size(options.paper.lower())
            if not dim_mm:
                raise Exception('Incorrect paper format: ' + options.paper)
            if portrait:
                dim_mm = [dim_mm[1], dim_mm[0]]
        elif options.size:
            dim_mm = options.size
        if dim_mm and options.margin:
            dim_mm[0] = max(0, dim_mm[0] - options.margin * 2)
            dim_mm[1] = max(0, dim_mm[1] - options.margin * 2)

        # ppi and scale factor are the same thing
        if options.ppi:
            ppmm = options.ppi / 25.4
            settings.scale_factor = options.ppi / 90.7
        else:
            settings.scale_factor = options.factor
            ppmm = 90.7 / 25.4 * settings.scale_factor

        # svg / pdf can be scaled only in cairo mode
        if settings.scale_factor != 1 and settings.need_cairo and not HAS_CAIRO:
            logging.error('Warning: install pycairo for using --factor or --ppi')
            settings.scale_factor = 1
            ppmm = 90.7 / 25.4

        # convert physical size to pixels
        if options.size_px:
            settings.size = options.size_px
        elif dim_mm:
            settings.size = [int(round(dim_mm[0] * ppmm)), int(round(dim_mm[1] * ppmm))]

        if settings.size and settings.size[0] + settings.size[1] <= 0:
            raise Exception('Both dimensions are less or equal to zero')

        if options.bbox:
            settings.bbox = options.bbox

        # scale can be specified with zoom or with 1:NNN scale
        fix_scale = False
        if options.zoom:
            settings.scale = 2 * 3.14159 * 6378137 / 2 ** (options.zoom + 8) / settings.scale_factor
        elif options.scale:
            settings.scale = options.scale * 0.00028 / settings.scale_factor
            # Now we have to divide by cos(lat), but we might not know latitude at this point
            # TODO: division should only happen for EPSG:3857 or not at all
            if options.center:
                settings.scale = settings.scale / math.cos(math.radians(options.center[1]))
            elif options.bbox:
                settings.scale = settings.scale / math.cos(math.radians((options.bbox[3] + options.bbox[1]) / 2))
            else:
                fix_scale = True

        # all calculations are in EPSG:3857 projection (it's easier)
        if settings.bbox:
            settings.bbox = settings.transform.forward(mapnik.Box2d(*settings.bbox))
            bbox_web_merc = TRANSFORM_LONLAT_WEBMERC.forward(mapnik.Box2d(*(options.bbox)))
            if settings.scale:
                settings.scale = Nik4Image.correct_scale(settings.bbox, settings.scale, bbox_web_merc, settings.bbox)

        # calculate bbox through center, zoom and target size
        if not settings.bbox and options.center and settings.size and settings.size[0] > 0 and settings.size[1] > 0 and settings.scale:
            # We don't know over which latitude range the bounding box spans, so we
            # first do everything in Web Mercator.
            center = TRANSFORM_LONLAT_WEBMERC.forward(mapnik.Coord(*options.center))
            w = settings.size[0] * settings.scale / 2
            h = settings.size[1] * settings.scale / 2
            bbox_web_merc = mapnik.Box2d(center.x-w, center.y-h, center.x+w, center.y+h)
            settings.bbox = TRANSFORM_LONLAT_WEBMERC.backward(bbox_web_merc)
            settings.bbox = settings.transform.forward(settings.bbox)
            # now correct the scale
            settings.scale = Nik4Image.correct_scale(settings.bbox, settings.scale, bbox_web_merc, settings.bbox)
            center = settings.transform.forward(mapnik.Coord(*options.center))
            w = settings.size[0] * settings.scale / 2
            h = settings.size[1] * settings.scale / 2
            settings.bbox = mapnik.Box2d(center.x-w, center.y-h, center.x+w, center.y+h)
        return settings

    @staticmethod
    def correct_scale(bbox, scale, bbox_web_merc, bbox_target):
        # correct scale if output projection is not EPSG:3857
        x_dist_merc = bbox_web_merc.maxx - bbox_web_merc.minx
        x_dist_target = bbox.maxx - bbox.minx
        return scale * (x_dist_target / x_dist_merc)

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
