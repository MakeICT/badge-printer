# MakeICT Badge Printer

This program streamlines part of the onboarding process at [MakeICT](http://makeict.org) - a nonprofit, volunteer-ran, community makerspace.

The program captures images from a webcam and personal information for use with a template to print out.

## Table of Contents

* [Installation](#installation)
* [Usage](#usage)
* [Support](#support)
* [Contributing](#contributing)

## Installation

Install the following dependencies
* `PyQT5`, including:
	* `QtWebEngine` (`python3-pyqt5.qtwebkit`)
	* `QtMultimedia`
* `gstreamer1.0-plugins-bad`
* `pyqrcode`
* `pypng`

## Usage

```sh
$ python3 badge-printer
```

### Templates
Templates must be SVG, and it's only been tested with Inkscape SVG's. The following embedded image fields are supported:
* `<image id="photo">` - aspect ratio should match your camera
* `<img id="qr">` - aspect ratio should be square

The following `<text>` fields are also supported:
* `<text id="firstName">`
* `<text id="lastName">`
* `<text id="title">`

## Support

Please [open an issue](https://github.com/makeict/badge-printer/issues/new) for support.

## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and [open a pull request](https://github.com/fraction/readme-boilerplate/compare/).
