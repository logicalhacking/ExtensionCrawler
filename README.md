# ExtensionCrawler
A collection of utilities for downloading and analyzing browser
extension from the Chrome Web store.

* `crawler`: A crawler for extensions from the Chrome Web Store. 
* `crx-tool`: A tool for analyzing and extracting `*.crx` files
  (i.e., Chrome extensions). Calling `crx-tool.py <extension>.crx`
  will check the integrity of the extension.
* `create-db`: A tool for creating/initializing the database files 
  from already existing extension archives.

The utilities store the extensions in the following directory 
hierarchy:
```
   archive
   ├── conf
   │   └── forums.conf
   ├── data
   │   └── ...
   └── log
       └── ...
```
The crawler downloads the most recent extension (i.e., the `*.crx`
file as well as the overview page. In addition, the `conf` directory 
may contain one file, called `forums.conf` that lists the ids of 
extensions for which the forums and support pages should be downloaded
as well.  The `data` directory will contain the downloaded extensions 
as well as sqlite files containing the extracted meta data. The sqlite
files can easily be re-generated using the `create-db` tool. 

All utilities are written in Python 3.x. The required modules are listed
in the file `requirements.txt`.

## Team
* [Achim D. Brucker](http://www.brucker.ch/)
* [Michael Herzberg](http://www.dcs.shef.ac.uk/cgi-bin/makeperson?M.Herzberg)

## License
This project is licensed under the GPL 3.0 (or any later version). 
