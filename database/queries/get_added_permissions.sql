select downloads, eu.extid, name, permission, new_crx_etag
from extension_update eu join extension e on eu.extid=e.extid and eu.first_date_with_new_crx_etag=e.date
join permission p on eu.new_crx_etag=p.crx_etag
where
  permission in (
    "<all_url>",
    "http://*/*",
    "https://*/*",
    "webRequest",
    "webRequestBlocking"
  )
and
  permission not in (select permission from permission where crx_etag=previous_crx_etag)
and
  first_date_with_new_crx_etag > NOW() - INTERVAL 2 DAY
order by downloads desc;
