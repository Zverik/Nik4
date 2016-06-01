# Nik4 Change History

## 1.6, 1.06.2016

* `--version` option.
* Added `--fonts` option for registering additional fonts. [#16](https://github.com/Zverik/Nik4/issues/16)
* Fixed `--center` with `--scale` error. [#18](https://github.com/Zverik/Nik4/issues/18)
* Swapped sizes 4A0 and 2A0. [#17](https://github.com/Zverik/Nik4/issues/17)
* Support Python 3. [#23](https://github.com/Zverik/Nik4/issues/23)

## 1.5, 7.12.2014

* Removed debug output for `--url`.
* Substitute variables with default values when `--vars` is empty.
* `--just-tiles` option for keeping tiles instead of merging them, also creates ozi/wld files if needed. [#15](https://github.com/Zverik/Nik4/issues/15)

## 1.4, 4.06.2014

* **Breaking change:** width and height specified in `--size` and `--size-px` are now swapped if they fit bbox better that way. Use `--norotate` to preserve old behaviour (that is, to force `WIDTH HEIGHT` order).
* You can specify 0 for one of the dimensions: first one is considered "long" side, the second is "short". E.g. for "portrait" bbox size "0 123" could become "123 200". `--norotate` option also applies to this. [#10](https://github.com/Zverik/Nik4/issues/10)
* Added `--dpi`, a synonim for `--ppi`.
* Now allowing underscores in variable names.
* Streaming output to `-` (stdout) now works. [#9](https://github.com/Zverik/Nik4/issues/9)

## 1.3, 22.05.2014

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
