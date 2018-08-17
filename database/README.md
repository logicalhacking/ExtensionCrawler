# Introduction

The extension crawler downloads all metadata and extension files into tar files.
This is great for archival, but not so great for analyzing the data. The crawler
therefore also supports inserting all newly crawled information into a MariaDB
database.  Additionally, there exists a script to regenerate the database from
old tar files.


# Setting up the database

## Hardware requirements

The database is meant to be setup on a (old) PC, although it should also work
with common cloud offerings.

The amount of data that the database needs to handle grows over time. Currently,
containing ~18 months worth of data, the database requires ~150GB of space.

It is recommended to have at least 16GB of RAM to keep the indices available;
less RAM might work, more RAM will certainly speed queries up. It is also good
to have at least 16GB of swap; while this detrimental to the performance of
MariaDB, it is often better than it being killed by the OS.

For storage, it is beneficial to have at least one HDD and one SSD, as the
database workload can be split into sequential and random IO.


## Configuration

A commented configuration file for MariaDB can be found in `config/my.cnf`.
Configuration options such as pool size and storage locations will need to be
adjusted.

## Table schemas

To set up the tables and schemas, make sure that you have the credentials for
root in your `~/.my.cnf` file, and execute the following:
```bash
mysql -e "create database extensions;"
for f in schemas/*.sql; do mysql extensions < $f; done
for f in views/*.sql; do mysql extensions < $f; done
```

# Maintaining the database

## Memory consumption

MariaDB will, at times, use much more memory than specified for the pool size --
100GB with a pool size of 4GB is certainly possible while regenerating the data.
In these cases, the database should be restarted. The crawler and regeneration
script will retry their database operations by default for around one hour.

## Backup

Regenerating the whole data set can take days, if not weeks, so even though all
data can be restored, having a backup speeds up recovery. For this purpose, the
MariaDB binary log is enabled to allow physical backups, which are much faster
than logical backups for our case. The folder `scripts/` contains scripts to do
full and incremental backups, as well as scripts to backup the schemas and users
(including permissions and hashed passwords).

# Regenerating extension data

When the crawler is changed to extract more or different data from the
extensions, one will probably want to regenerate all data, i.e., ask the crawler
to go through all existing tar files and re-extract the already downloaded data.
In order to do so, the `create-db` or `sge/create-db.sh` (for HPCs) can be used.
More information can be found when calling these scripts with `--help`.

# Using the data set

## Example queries

For more (commented) queries, see the `queries/` folder.

- ```sql
select extid,crx_etag,count(filename) from extension_most_recent_small join crxfile using (crx_etag) where filename like '%.js' group by extid,crx_etag limit 10;
```
This query will print the number of JavaScript files per extension.

## Table schemas

All schema files can be found in the `schemas/` folder.

| Table name | Description |
| --- | --- |
| extension | General extension metadata from the store pages. One row per \
extension and crawldate (!). If you are only interested in the most recent \
*view* of the Chrome Web Store, use the `extension_most_recent` view. For \
testing your queries, suffix either table/view with *\_small* to only get \
roughly 1/256th of all extensions. |
| status | The HTTP status codes for the store page and `crx` download. |
| crx | General metadata of the extension file (the `crx` archive itself). Also \
contains the manifest. |
| crxfile | General metadata of the extension files, e.g., the files contained \
in the `crx` archives (JavaScript files, etc.).|
| category | Categories of the extensions, e.g. *productivity*, *office*, \
or *game*. |
| permission | Permissions found in the manifests, e.g., *webRequest*, *tab*, but also \
host permissions such as *https://www.google.com*. |
| content_script_url | Content script URLs found in the manifest. These are the \
URLs where the extensions request to have a content script executed when the \
user visits the website. |
| libdet | Information about used libraries. For each file found in `crx` \
archives (identified by MD5 sums), this table stores classifications of the \
file, e.g., whether it is a certain library. |
| review{,\_comment} | Post-metadata and posts from the review forum of an extension. |
| support{,\_comment} | Post-metadata and posts from the support forum of an extension. |
| reply{,\_comment} | Reply-post-metadata and posts for both the review and support forums. |

## Views

All views can be found in the `views/` folder.

| View name | Description |
| --- | --- |
| extension_small | Contains only roughly 1/256th of all extensions. |
| extension_most_recent | Instead of one row for every combination of extension \
id and crawl date, this view only contains the rows from the most recent crawl \
date. |
| extension_most_recent_small | Same, but roughly only 1/256th of all extensions. |
| extension_second_most_recent | Similar to `extension_most_recent`, but \
contains the second-most recent entry for all extensions. This is useful for \
investigating how extensions change. |
| extension_{most,second_most}_recent_until_date | Parameterized query. Only \
considers extensions crawled before a given date. Usage:  \
```sql
select * from (select @until_date:='2018-05-25') foo, extension_most_recent_until_date;
``` |
| extension_update | Selects all extension updates in the database. A row in the result represents \
one extension update, with the date and crx_etag when we have first seen the \
update, and the date and crx_etag when we have last seen the old version. As \
we crawl every night, the difference should be around 24 hours on average. |
