# Nik4 Change History

## 1.3, *master*

* Fixed value order in world files.
* Added more paper formats. [#7](https://github.com/Zverik/Nik4/issues/7)
* Style XML can now be streamed from stdin.
* Style XML can now contain variables `${name:default}`, set them with `--vars name=value`. [#6](https://github.com/Zverik/Nik4/issues/6)

## 1.2, 19.05.2014

* Fixed georeferencing of tiled maps. [#4](https://github.com/Zverik/Nik4/issues/4)
* World files are now written in EPSG:3857 projection.
* Added `--url` option for leaflet / openlayers map URLs. [#5](https://github.com/Zverik/Nik4/issues/5)

## 1.1, 18.05.2014

* True scale (like 1:10000) was calculated incorrectly. [#3](https://github.com/Zverik/Nik4/issues/3)
* Mapnik image size limit (16384×16384) is now enforced.
* Fixed breaking of large tiled maps.

## 1.0, 16.05.2014

Initial release
