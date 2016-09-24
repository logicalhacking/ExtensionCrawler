# ExtensionCrawler
A collection of utilities for downloading and analyzing browser
extension from the Chrome Web store.

* `crawler.py`: A crawler for extensions from the Chrome Web
  Store. Calling `crawler.py` will downloads 200 extensions from all
  categories into a folder `downloaded` in the current directory. In
  case an extension has already been downloaded, the script skips it.
* `permstats.py`: A tool for generating statistical data from the
  crawled extensions. 
* `crx-tool.py`: A tool for analyzing `*.crx` files (i.e., Chrome
  extensions). Calling `crx-tool.py <extension>.crx` will check the
  integrity of the extension. 

All Utilities are written in Pythen 3.x. 

##
* [Achim D. Brucker](http://www.brucker.ch/)
* [Michael Herzberg](http://www.dcs.shef.ac.uk/cgi-bin/makeperson?M.Herzberg)

## License
This project is licensed under the GPL 3.0 (or any later version). 
