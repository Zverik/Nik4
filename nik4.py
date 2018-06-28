#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Nik4: Export image from mapnik
# Run it with -h to see the list of options
# Written by Ilya Zverev, licensed WTFPL

import mapnik
import sys
import os
import re
import argparse
import math
import tempfile
import logging
import codecs

from nik4.nik4_image import Nik4Image, EPSG_3857

try:
    import cairo
    HAS_CAIRO = True
except ImportError:
    HAS_CAIRO = False

TILE_BUFFER = 128
IM_MONTAGE = 'montage'



def layer_bbox(m, names, proj_target, bbox=None):
    """Calculate extent of given layers and bbox"""
    for layer in (l for l in m.layers if l.name in names):
        # it may as well be a GPX layer in WGS84
        layer_proj = mapnik.Projection(layer.srs)
        box_trans = mapnik.ProjTransform(layer_proj, proj_target)
        lbbox = box_trans.forward(layer.envelope())
        if bbox:
            bbox.expand_to_include(lbbox)
        else:
            bbox = lbbox
    return bbox


def filter_layers(m, lst):
    """Leave only layers in list active, disable others"""
    for l in m.layers:
        l.active = l.name in lst


def select_layers(m, enable, disable):
    """Enable and disable layers in corresponding lists"""
    for l in m.layers:
        if l.name in enable:
            l.active = True
        if l.name in disable:
            l.active = False


def prepare_ozi(mbbox, mwidth, mheight, name, transform):
    """Create georeferencing file for OziExplorer"""
    def deg(value, is_lon):
        degrees = math.floor(abs(value))
        minutes = (abs(value) - degrees) * 60
        return '{:4d},{:3.5F},{}'.format(
            int(round(degrees)), minutes,
            ('W' if is_lon else 'S') if value < 0 else ('E' if is_lon else 'N'))

    ozipoint = ('Point{:02d},xy,     ,     ,in, deg,    ,        ,N,    ,        ,E' +
                ', grid,   ,           ,           ,N')
    bbox = transform.backward(mbbox)
    points = "\n".join([ozipoint.format(n) for n in range(3, 31)])
    header = '''OziExplorer Map Data File Version 2.2
Nik4
{name}
1 ,Map Code,
WGS 84,WGS 84,   0.0000,   0.0000,WGS 84
Reserved 1
Reserved 2
Magnetic Variation,,,E
Map Projection,Mercator,PolyCal,No,AutoCalOnly,No,BSBUseWPX,No
Point01,xy,    0,    0,in, deg,{top},{left}, grid,   ,           ,           ,N
Point02,xy, {width:4d}, {height:4d},in, deg,{bottom},{right}, grid,   ,           ,           ,N
{points}
Projection Setup,,,,,,,,,,
Map Feature = MF ; Map Comment = MC     These follow if they exist
Track File = TF      These follow if they exist
Moving Map Parameters = MM?    These follow if they exist
MM0,Yes
MMPNUM,4
MMPXY,1,0,0
'''.format(name=name,
           top=deg(bbox.maxy, False),
           left=deg(bbox.minx, True),
           width=mwidth - 1,
           height=mheight - 1,
           bottom=deg(bbox.miny, False),
           right=deg(bbox.maxx, True),
           points=points)
    return ''.join([
        header,
        "MMPXY,2,{},0\n".format(mwidth),
        "MMPXY,3,{},{}\n".format(mwidth, mheight),
        "MMPXY,4,0,{}\n".format(mheight),
        'MMPLL,1,{:4.6f},{:4.6f}\n'.format(bbox.minx, bbox.maxy),
        'MMPLL,2,{:4.6f},{:4.6f}\n'.format(bbox.maxx, bbox.maxy),
        'MMPLL,3,{:4.6f},{:4.6f}\n'.format(bbox.maxx, bbox.miny),
        'MMPLL,4,{:4.6f},{:4.6f}\n'.format(bbox.minx, bbox.miny),
        "MM1B,{}\n".format((mbbox.maxx - mbbox.minx) / mwidth * math.cos(
            math.radians(bbox.center().y))),
        "MOP,Map Open Position,0,0\n",
        "IWH,Map Image Width/Height,{},{}\n".format(mwidth, mheight),
    ])


def prepare_wld(bbox, mwidth, mheight):
    """Create georeferencing world file"""
    pixel_x_size = (bbox.maxx - bbox.minx) / mwidth
    pixel_y_size = (bbox.maxy - bbox.miny) / mheight
    left_pixel_center_x = bbox.minx + pixel_x_size * 0.5
    top_pixel_center_y = bbox.maxy - pixel_y_size * 0.5
    return ''.join(["{:.8f}\n".format(n) for n in [
        pixel_x_size, 0.0,
        0.0, -pixel_y_size,
        left_pixel_center_x, top_pixel_center_y
    ]])


def write_metadata(bbox, mwidth, mheight, transform, img_output_file, wld_file=None, ozi_file=None):
    """Write worldfile and/or OZI file if required.

    Parameters
    ----------
    bbox: mapnik.Box2d
        bounding box of the map
    mwidth : int
        width of the image
    mheight : int
        height of the image
    transform : mapnik.ProjTransform
        transformation from EPSG:4326 to the target projection
    img_output_file : str
        image output path (required for OZI file)
    wld : file
        file pointer to the world file to be written (or None if non has to be written)
    ozi : file
        file pointer to the OZI file to be written (or None if non has to be written)
    """
    if ozi_file:
        ozi_file.write(prepare_ozi(bbox, mwidth, mheight, img_output_file, transform))
    if wld_file:
        wld_file.write(prepare_wld(bbox, mwidth, mheight))


def xml_vars(style, variables):
    """Replace ${name:default} from style with variables[name] or 'default'"""
    # Convert variables to a dict
    v = {}
    for kv in variables:
        keyvalue = kv.split('=', 1)
        if len(keyvalue) > 1:
            v[keyvalue[0]] = keyvalue[1].replace('&', '&amp;').replace(
                '<', '&lt;').replace('>', '&gt;').replace(
                '"', '&quot;').replace("'", '&#39;')
    if not v:
        return style
    # Scan all variables in style
    r = re.compile(r'\$\{([a-z0-9_]+)(?::([^}]*))?\}')
    rstyle = ''
    last = 0
    for m in r.finditer(style):
        if m.group(1) in v:
            value = v[m.group(1)]
        elif m.group(2) is not None:
            value = m.group(2)
        else:
            raise Exception('Found required style parameter: ' + m.group(1))
        rstyle = rstyle + style[last:m.start()] + value
        last = m.end()
    if last < len(style):
        rstyle = rstyle + style[last:]
    return rstyle


def reenable_layers(style, layers):
    """Remove status=off from layers we need."""
    layer_select = '|'.join([l.replace('\\', '\\\\').replace('|', '\\|')
                             .replace('.', '\\.').replace('+', '\\+')
                             .replace('*', '\\*') for l in layers])
    style = re.sub(
        r'(<Layer[^>]+name=["\'](?:{})["\'][^>]+)status=["\']off["\']'.format(layer_select),
        r'\1', style, flags=re.DOTALL)
    style = re.sub(
        r'(<Layer[^>]+)status=["\']off["\']([^>]+name=["\'](?:{})["\'])'.format(layer_select),
        r'\1\2', style, flags=re.DOTALL)
    return style


def parse_layers_string(layers):
    if not layers:
        return []
    return [l1 for l1 in (l.strip() for l in layers.split(',')) if l1]


def add_fonts(path):
    if os.path.exists(path):
        mapnik.register_fonts(path)
    else:
        raise Exception('The directory "{p}" does not exists'.format(p=path))


def run(options, settings):
    # reading style xml into memory for preprocessing
    if options.style == '-':
        style_xml = sys.stdin.read()
        style_path = ''
    else:
        with codecs.open(options.style, 'r', 'utf-8') as style_file:
            style_xml = style_file.read()
        style_path = os.path.dirname(options.style)
    if options.base:
        style_path = options.base
    if options.vars:
        style_xml = xml_vars(style_xml, options.vars)
    if options.layers or options.add_layers:
        style_xml = reenable_layers(
            style_xml, parse_layers_string(options.layers) +
            parse_layers_string(options.add_layers))

    # for layer processing we need to create the Map object
    m = mapnik.Map(100, 100)  # temporary size, will be changed before output
    mapnik.load_map_from_string(m, style_xml.encode("utf-8"), False, style_path)
    m.srs = settings.proj_target.params()

    # register non-standard fonts
    if options.fonts:
        for f in options.fonts:
            add_fonts(f)

    # get bbox from layer extents
    if options.fit:
        settings.bbox = layer_bbox(m, options.fit.split(','), settings.proj_target, settings.bbox)
        # here's where we can fix scale, no new bboxes below
        if settings.bbox and settings.fix_scale:
            settings.scale = settings.scale / math.cos(math.radians(settings.transform.backward(settings.bbox.center()).y))
        bbox_web_merc = Nik4Image.TRANSFORM_LONLAT_WEBMERC.forward(settings.transform.backward(settings.bbox))
        if settings.scale:
            settings.scale = Nik4Image.correct_scale(settings.bbox, settings.scale, bbox_web_merc, settings.bbox)
        # expand bbox with padding in mm
        if settings.bbox and options.padding and (settings.scale or settings.size):
            if settings.scale:
                tscale = settings.scale
            else:
                tscale = min((settings.bbox.maxx - settings.bbox.minx) / max(settings.size[0], 0.01),
                             (settings.bbox.maxy - settings.bbox.miny) / max(settings.size[1], 0.01))
            settings.bbox.pad(options.padding * settings.ppmm * tscale)

    # bbox should be specified by this point
    if not settings.bbox:
        raise Exception('Bounding box was not specified in any way')

    # rotate image to fit bbox better
    if settings.rotate and settings.size:
        portrait = settings.bbox.maxy - settings.bbox.miny > settings.bbox.maxx - settings.bbox.minx
        # take into consideration zero values, which mean they should be calculated from bbox
        if (settings.size[0] == 0 or settings.size[0] > settings.size[1]) and portrait:
            settings.size = [settings.size[1], settings.size[0]]

    # calculate pixel size from bbox and scale
    if not settings.size:
        if settings.scale:
            settings.size = [int(round(abs(settings.bbox.maxx - settings.bbox.minx) / settings.scale)),
                    int(round(abs(settings.bbox.maxy - settings.bbox.miny) / settings.scale))]
        else:
            raise Exception('Image dimensions or scale were not specified in any way')
    elif settings.size[0] == 0:
        settings.size[0] = int(round(settings.size[1] * (settings.bbox.maxx - settings.bbox.minx) / (settings.bbox.maxy - settings.bbox.miny)))
    elif settings.size[1] == 0:
        settings.size[1] = int(round(settings.size[0] / (settings.bbox.maxx - settings.bbox.minx) * (settings.bbox.maxy - settings.bbox.miny)))

    if options.output == '-' or (settings.need_cairo and (options.tiles_x > 1 or options.tiles_y > 1)):
        options.tiles_x = 1
        options.tiles_y = 1
    max_img_size = max(settings.size[0] / options.tiles_x, settings.size[1] / options.tiles_y)
    if max_img_size > 16384:
        raise Exception('Image size exceeds mapnik limit ({} > {}), use {}--tiles'.format(
           max_img_size , 16384, 'a larger value for ' if options.tiles_x > 1 or options.tiles_y > 1 else ''))

    # add / remove some layers
    if options.layers:
        filter_layers(m, parse_layers_string(options.layers))
    if options.add_layers or options.hide_layers:
        select_layers(m, parse_layers_string(options.add_layers),
                      parse_layers_string(options.hide_layers))

    logging.debug('scale=%s', settings.scale)
    logging.debug('scale_factor=%s', settings.scale_factor)
    logging.debug('size=%s,%s', settings.size[0], settings.size[1])
    logging.debug('bbox=%s', settings.bbox)
    logging.debug('bbox_wgs84=%s', settings.transform.backward(settings.bbox) if settings.bbox else None)
    logging.debug('layers=%s', ','.join([l.name for l in m.layers if l.active]))

    # export image
    m.aspect_fix_mode = mapnik.aspect_fix_mode.GROW_BBOX
    m.resize(settings.size[0], settings.size[1])
    m.zoom_to_box(settings.bbox)
    logging.debug('m.envelope(): {}'.format(m.envelope()))

    outfile = options.output
    if options.output == '-':
        outfile = tempfile.TemporaryFile(mode='w+b')

    if settings.need_cairo:
        if HAS_CAIRO:
            if settings.fmt == 'svg':
                surface = cairo.SVGSurface(outfile, settings.size[0], settings.size[1])
            else:
                surface = cairo.PDFSurface(outfile, settings.size[0], settings.size[1])
            mapnik.render(m, surface, settings.scale_factor, 0, 0)
            surface.finish()
        else:
            mapnik.render_to_file(m, outfile, settings.fmt)
        write_metadata(m.envelope(), settings.size[0], settings.size[1], settings.transform, options.output, options.wld, options.ozi)
    else:
        if options.tiles_x == options.tiles_y == 1:
            im = mapnik.Image(size[0], size[1])
            mapnik.render(m, im, settings.scale_factor)
            im.save(outfile, fmt)
            write_metadata(m.envelope(), settings.size[0], settings.size[1], settings.transform, options.output, options.wld, options.ozi)
        else:
            # we cannot make mapnik calculate scale for us, so fixing aspect ratio outselves
            rdiff = (settings.bbox.maxx-settings.bbox.minx) / (settings.bbox.maxy-settings.bbox.miny) - settings.size[0] / settings.size[1]
            if rdiff > 0:
                settings.bbox.height((settings.bbox.maxx - settings.bbox.minx) * settings.size[1] / settings.size[0])
            elif rdiff < 0:
                settings.bbox.width((settings.bbox.maxy - settings.bbox.miny) * settings.size[0] / settings.size[1])
            settings.scale = (settings.bbox.maxx - settings.bbox.minx) / settings.size[0]
            width = max(32, int(math.ceil(1.0 * settings.size[0] / options.tiles_x)))
            height = max(32, int(math.ceil(1.0 * settings.size[1] / options.tiles_y)))
            m.resize(width, height)
            m.buffer_size = TILE_BUFFER
            tile_cnt = [int(math.ceil(1.0 * settings.size[0] / width)),
                        int(math.ceil(1.0 * settings.size[1] / height))]
            logging.debug('tile_count=%s %s', tile_cnt[0], tile_cnt[1])
            logging.debug('tile_size=%s,%s', width, height)
            tmp_tile = '{:02d}_{:02d}_{}'
            tile_files = []
            for row in range(0, tile_cnt[1]):
                for column in range(0, tile_cnt[0]):
                    logging.debug('tile=%s,%s', row, column)
                    tile_bbox = mapnik.Box2d(
                        settings.bbox.minx + 1.0 * width * settings.scale * column,
                        settings.bbox.maxy - 1.0 * height * settings.scale * row,
                        settings.bbox.minx + 1.0 * width * settings.scale * (column + 1),
                        settings.bbox.maxy - 1.0 * height * settings.scale * (row + 1))
                    tile_size = [
                        width if column < tile_cnt[0] - 1 else settings.size[0] - width * (tile_cnt[0] - 1),
                        height if row < tile_cnt[1] - 1 else settings.size[1] - height * (tile_cnt[1] - 1)]
                    m.zoom_to_box(tile_bbox)
                    im = mapnik.Image(tile_size[0], tile_size[1])
                    mapnik.render(m, im, settings.scale_factor)
                    tile_name = tmp_tile.format(row, column, options.output)
                    im.save(tile_name, settings.fmt)
                    if options.just_tiles:
                        # write ozi/wld for a tile if needed
                        if '.' not in tile_name:
                            tile_basename = tile_name + '.'
                        else:
                            tile_basename = tile_name[0:tile_name.rindex('.')+1]
                        if options.ozi:
                            with open(tile_basename + 'ozi', 'w') as f:
                                f.write(prepare_ozi(tile_bbox, tile_size[0], tile_size[1],
                                                    tile_basename + '.ozi', settings.transform))
                        if options.wld:
                            with open(tile_basename + 'wld', 'w') as f:
                                f.write(prepare_wld(tile_bbox, tile_size[0], tile_size[1]))
                    else:
                        tile_files.append(tile_name)
            if not options.just_tiles:
                # join tiles and remove them if joining succeeded
                import subprocess
                result = subprocess.call([
                    IM_MONTAGE, '-geometry', '+0+0', '-tile',
                    '{}x{}'.format(tile_cnt[0], tile_cnt[1])] +
                    tile_files + [options.output])
                if result == 0:
                    for tile in tile_files:
                        os.remove(tile)
                    write_metadata(bbox, size[0], size[1], transform, options.output, options.wld, options.ozi)

    if options.output == '-':
        if sys.platform == "win32":
            # fix binary output on windows
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

        outfile.seek(0)
        sys.stdout.write(outfile.read())
        outfile.close()


if __name__ == "__main__":
    options = Nik4Image.get_argument_parser().parse_args()

    options.tiles_x = 0
    options.tiles_y = 0

    if options.tiles:
        if options.tiles.isdigit():
            options.tiles_x = int(options.tiles)
            options.tiles_y = options.tiles_x
        else:
            match = re.search(r'^(\d+)x(\d+)$', options.tiles)
            if match:
               options.tiles_x = int(match.group(1))
               options.tiles_y = int(match.group(2))
        if not 1 <= options.tiles_x * options.tiles_y <= 144:
            raise Exception('--tiles needs positive integer argument, or two integers separated by x; max. number of tiles is 144')

    if options.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
    settings = Nik4Image(options, HAS_CAIRO)
    settings.setup_options()
    logging.info(settings.__dict__)
    run(options, settings)
