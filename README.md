# MakeICT Badge Printer

This program streamlines part of the onboarding process at [MakeICT](http://makeict.org) - a nonprofit, volunteer-ran, community makerspace.

The program captures images from a webcam and personal information for use with a template to print out.

## Table of Contents

* [Installation](#installation)
* [Usage](#usage)
* [Support](#support)
* [Contributing](#contributing)

## Installation

Install the following dependencies:
* `gstreamer1.0-plugins-bad`
* `libqt5multimedia5-plugins`
* `pyqt5`, including:
	* `QtWebEngine`
	* `QtMultimedia`
* `pyqrcode`
* `pypng`

`pip` is recommended for all Python dependencies.

## Usage

```sh
$ python3 badge-printer
```
### Quick Print

Quick Print is an easy way to expedite the printing process for batches of nametags.
1. First, select a template and enter details as you normally would.
2. Next, make sure the correct printer is selected in the Quick Print selector.
3. Lastly, hit the print button in the Quick Print section.

For even faster processing, pressing the "ENTER" key while in any template field will send the file to the selected printer. After Quick Print is triggered, focus is moved to the first template field to prepare you for the next entry.


### Templates
Templates must be SVG, and it's only been tested with Inkscape SVG's. The following embedded image fields are supported:
* `<image id="photo">` - `preserveAspectRatio` attribute should be `xMidYMid slice`
* `<image id="qr">` - `width` and `height` attributes should be square

The program will recognize `<text>` fields with an `id` set. These will appear in the form and be editable.

Note: this probably isn't the best way to do this. Maybe a custom namespace?

## Support

Please [open an issue](https://github.com/makeict/badge-printer/issues/new) for support.

## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and [open a pull request](https://github.com/fraction/readme-boilerplate/compare/).
