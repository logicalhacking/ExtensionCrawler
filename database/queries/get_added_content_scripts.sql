select downloads, eu.extid, name, url, new_crx_etag
from extension_update eu join extension e on eu.extid=e.extid and eu.first_date_with_new_crx_etag=e.date
join content_script_url c on eu.new_crx_etag=c.crx_etag
where
  url in (
    "file://*/*",
    "http://*/*",
    "https://*/*",
    "*://*/*",
    "<all_urls>"
  )
and
  url not in (select url from content_script_url where crx_etag=previous_crx_etag)
and
  first_date_with_new_crx_etag > NOW() - INTERVAL 2 DAY
order by downloads desc;
