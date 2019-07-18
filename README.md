# Nik4

This is a mapnik-to-image exporting script. It requires only `mapnik-python` bindings.
Install it with `pip install nik4` or `easy_install nik4` and run with `-h` option
to see available options and their descriptions.

## Why is it better

Nik4 takes great care to preserve values you feed it. If you say you need a 800×600 image,
it won't take a pixel less or more. It won't shrink a bounding box or distort lines when
specifying so called "scale factor". When you need a 300 dpi image, you tell it `--ppi 300`
and can be sure you will get what you intended.

For example, this is a sample rendering of an area in Tallinn on zoom 17, by Nik4, Nik2img
and as seen on the default layer on osm.org:

![nik4 - osm.org - nik2img](img/demo-zoom-levels.png)

Also it can use real-world units, that is, millimeters (and prefers to). Specify dimensions
for printing, choose bounding box and ppi scale — and the result won't disappoint. Options
are intuitive and plenty, and you will be amazed how much tasks became simpler with Nik4.

## How to use it

Again, run `nik4.py -h` to see the list of all available options. Here are some examples.

### Watch a mapping party area

First, if you haven't already, install PostgreSQL+PostGIS and Mapnik, and use osm2pgsql
to populate the database with a planet extract. For instructions see
[here](http://switch2osm.org/loading-osm-data/) or [here](http://wiki.openstreetmap.org/wiki/User:Zverik/Tile_Server_on_Fedora_20).
Get bounds by visiting [osm.org](http://openstreetmap.org): click "Export" and "Choose another region". Then:

    nik4.py -b -0.009 51.47 0.013 51.484 -z 17 openstreetmap-carto/osm.xml party-before.png

Here `osm.xml` is the compiled Mapnik style.
Then you can [update](http://wiki.openstreetmap.org/wiki/Minutely_Mapnik) you database and generate
snapshots of an area as it is being mapped. Alternatively, you can specify an area with its center
and desired image size in pixels:

    nik4.py -c 0 51.477 --size-px 800 600 -z 17 openstreetmap-carto/osm.xml party-before.png

Even simpler, instead of `--center` and `--zoom` options, just grab an URL of a place:

    nik4.py --url http://www.openstreetmap.org/#map=16/55.9865/37.2160 osm.xml screenshot.png

### Make a georeferenced raster image

Some people prefer planning routes with OziExplorer or similar programs. Or want to take a big
raster map with them on the road. For that a very big image is needed. Usually they turn to
downloading and stitching hundreds of tiles, but with Nik4 you can make Mapnik produce a better
looking map, faster and without bothering tile server administrators.

Since you are not bound to any tile provider, you should employ [TileMill](https://www.mapbox.com/tilemill/)
for customizing your map style: for example, remove forest on low zooms, add contrast to
road lines, render more villages, highlight useful POI and cycling routes.

    nik4.py -b 25 61.6 30.6 63.3 -z 13 custom.xml kuopio.png --ozi kuopio.map

This will render 16311×10709 image with a georeferencing file ready to open in OziExplorer.
For a `.wld` file, which can be used in desktop GIS applications or for creating a GeoTIFF file,
use `--wld` option. You can convert png+wld to geotiff with GDAL:

    gdal_translate -of GTiff -a_srs epsg:4326 image.png image.tif

### Make a BIG raster image

You would likely encounter out of memory error while trying to generate 16311×10709 image from the last
chapter. Despair not:

    nik4.py -b 25 61.6 30.6 63.3 -z 13 custom.xml kuopio.png --ozi kuopio.map --tiles 4

Voilà — now Mapnik has to generate 16 images of a manageable size 4078×2678. After that Nik4 will call
`montage` from the Imagemagick package to stitch all tiles together.

What if `montage` cannot fit images into memory? There is a way, but you would need quite a lot of disk
space, several gigabytes:

    for i in *_kuopio.png; do convert $i `basename $i .png`.mpc; done
    montage -geometry +0+0 -tile 4x4 *_kuopio.mpc kuopio.png
    rm *_kuopio.{png,mpc,cache}

These lines will convert all images to Imagemagick's internal MPC format, from which `montage` reads directly.
You would need more space for a similar MPC cache of the output file. Note that most software will have
trouble opening an image surpassing 200 megapixels.

### Get an image for printing

![A4 options](img/paper-options.png)

Let's say you need a 1:5000 image of a city center for printing on a A4 sheet with margins.

    nik4.py -s 5000 --ppi 300 -a 4 -c 24.1094 56.9488 --margin 10 ~/osm/krym/carto/osm.xml 4print.png

What you get is a raster image, which when printed on an A4 with 300 dpi resolution, would have 10 mm margins
and scale of exactly 50 m in a cm. See the picture above for explanation of margins and other options.
Formats can be `a0-a9`, `letter`, `card` and so on.  The paper orientation depends on a bbox;
to force landscape or portrait orientation prepend the format with `+` or `-` characters.
Or don't bother and enter numbers by hand: `-d 150 100` will export a 15×10 postcard map.

### Wait, what's that again, about dimensions?

Dimensions you specify in `--size` (`-d`) and `--size-px` (`-x`) arguments are not exactly width and height
in that order: they will be swapped if a bounding box would fit better. For example, when you export
"landscape" bbox and specify `-d 200 400`, the image would be 40 cm wide and 20 cm tall. To prevent this
behaviour, use `--norotate` option: with it, that image would be 20 cm wide, with the bounding box
expanded vertically.

When you don't want your bounding box altered, use `0` for one of dimension values. The first one in that
case is considered a long side length, the second is for shorter side. With `--norotate` option, they
are width and height respectively. For example, `-x 1024 0 --norotate` would make the resulting image
1024 pixels wide regardless of bounding box proportions.

### Print a route

On the image above there is a route. Nik4 cannot parse GPX files or draw anything on top of exported
images, but it can manage layers in Mapnik style file. And Mapnik (via OGR plugin) can draw
[a lot of things](http://www.gdal.org/ogr/ogr_formats.html), including GPX, GeoJSON, CSV, KML.
Just add your route to the style like this:

```xml
<Style name="route" filter-mode="first">
  <Rule>
    <LineSymbolizer stroke-width="5" stroke="#012d64" stroke-linejoin="round" stroke-linecap="round" />
  </Rule>
</Style>
<Layer name="route" status="off" srs="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs">
    <StyleName>route</StyleName>
    <Datasource>
       <Parameter name="type">ogr</Parameter>
       <Parameter name="file">/home/user/route.gpx</Parameter>
       <Parameter name="layer">tracks</Parameter>
    </Datasource>
  </Layer>
```

Note that you can add it in any place: for example, between road and label layers, so the route does not
obscure any text. Also note `status="off"`: this layer won't be drawn by default. So if you want
to export a clean map for the extent of your route (or any other) layer, use those options:

    nik4.py --fit route --size-px 400 700 osm.xml route_area.png

To enable drawing of the layer, use `--add-layers` option:

    nik4.py --fit route --add-layers route,stops --ppi 150 -a 6 osm.xml route.png

You can list many layers, separating them with commas. And you can hide some layers:
`--hide-layers contours,shields`. Obviously you can fit several layers at once, as well
as specify a bounding box to include on a map. All layer names are case-sensitive, so if
something does not appear, check your style file for exact layer names.

### Print a different route each time

Nik4 supports variables in XML styles: `${name:default}` defines a variable with the given name
and its default value (which can be omitted, along with `:`). To substitute variable
definitions with values or defaults, use `--vars` parameter. For example, let's make
stroke width in the last example configurable, and request GPX file name:

```xml
    <LineSymbolizer stroke-width="${width:5}" stroke="#012d64" stroke-linejoin="round" stroke-linecap="round" />
    ...
      <Parameter name="file">${route}</Parameter>
```

Now to make an image of a route, use this command:

    nik4.py --fit route --ppi 150 -a 6 osm.xml route.png --vars width=8 route=~/routes/day2.gpx

Note that path would likely to be resolved relative to the XML file location. If you omit `route` variable
in this example, you'll get an error message.

### Generate a vector drawing from a map

It's as easy as adding an `.svg` extension to the output file name.

    nik4.py --fit route -a -5 --factor 4 osm.xml map.svg

Why did I use `--factor` (it's the same as using `--ppi 362.8`, which is 90.7 * 4)? Shouldn't
vector images be independent of the resolution? Well, the problem is in label kerning:

![SVG labels quality](img/svg-factor.png)

Left image was exported with `--factor 1`. You can see in "ali", "sis", "Uus" that distance between
letters is varying unpredictably, not like the font instructs. That's because Mapnik rounds letter widths
to nearest integers, that is, to pixels. By increasing the resolution, you make that granularity finer,
so rounding errors are much less prominent. Labels would become slightly longer, that's why they are
different in the second image.

You can export a map to PDF and be done with it, but often you'd want to do some postprocessing:
move labels away from roads, highlight features, draw additional labels and arrows. For that
I recommend processing the SVG file with [mapnik-group-text](https://github.com/Zverik/mapnik-group-text),
which would allow for easier label movement.

## See also

* [mapnik/demo/python](https://github.com/mapnik/mapnik/tree/master/demo/python)
* [generate\_image.py](http://svn.openstreetmap.org/applications/rendering/mapnik/generate_image.py)
* [mapnik-render-image](https://github.com/plepe/mapnik-render-image)
* [osm.org/export](https://trac.openstreetmap.org/browser/sites/tile.openstreetmap.org/cgi-bin/export)
* [nik2img](http://code.google.com/p/mapnik-utils/wiki/Nik2Img)

For generating tiles, see [polytiles.py](https://github.com/Zverik/polytiles).

## Author and license

The script was written by Ilya Zverev and published under WTFPL.
