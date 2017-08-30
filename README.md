# ExtensionCrawler

A collection of utilities for downloading and analyzing browser
extension from the Chrome Web store.

* `crawler`: A crawler for extensions from the Chrome Web Store.
* `crx-tool`: A tool for analyzing and extracting `*.crx` files
  (i.e., Chrome extensions). Calling `crx-tool.py <extension>.crx`
  will check the integrity of the extension.
* `crx-extract`: A simple tool for extracting `*.crx` files from the
   tar-based archive hierarchy.
* `crx-jsinventory`: Build a JavaScript inventory of a `*.crx` file using a
                   JavaScript decomposition analysis.
* `crx-jsstrings`: A tool for extracting code blocks, comment blocks, and
*                string literals from JavaScript.
* `create-db`: A tool for updating a remote MariaDB from already
   existing extension archives.
>>>>>>> bde59c50401448e346032219ab2130a31b3d7ec8

The utilities store the extensions in the following directory
hierarchy:

```shell
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
as well. The `data` directory will contain the downloaded extensions.

The `crawler` and `create-db` scripts will access and update a MariaDB.
They will use the host, datebase, and credentials found in `~/.my.cnf`.
Since they make use of various JSON features, it is recommended to use at
least version 10.2.8 of MariaDB.

All utilities are written in Python 3.x. The required modules are listed
in the file `requirements.txt`.

## Installation

Clone and use pip to install as a package.

```shell
git clone git@logicalhacking.com:BrowserSecurity/ExtensionCrawler.git
pip install -e ExtensionCrawler
```

## Team

* [Achim D. Brucker](http://www.brucker.ch/)
* [Michael Herzberg](http://www.dcs.shef.ac.uk/cgi-bin/makeperson?M.Herzberg)

### Contributors

* Mehmet Balande

## License

This project is licensed under the GPL 3.0 (or any later version).
