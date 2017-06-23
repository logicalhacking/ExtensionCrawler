# ExtensionCrawler
A collection of utilities for downloading and analyzing browser
extension from the Chrome Web store.

* `crawler`: A crawler for extensions from the Chrome Web Store. 
* `crx-tool`: A tool for analyzing and extracting `*.crx` files
  (i.e., Chrome extensions). Calling `crx-tool.py <extension>.crx`
  will check the integrity of the extension.

All utilities are written in Python 3.x. The following non-standard 
modules might be required:
* requests (`apt-get install python3-requests`) 
* dateutil (`apt-get install python3-dateutil`)
* jsmin (`apt-get  install python3-jsmin`)

## Team
* [Achim D. Brucker](http://www.brucker.ch/)
* [Michael Herzberg](http://www.dcs.shef.ac.uk/cgi-bin/makeperson?M.Herzberg)

## License
This project is licensed under the GPL 3.0 (or any later version). 
