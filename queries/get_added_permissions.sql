select extension_info.extid, extension_info.name, permission
from (
  -- We generate a table containing every crx_etag that we crawled within the
  -- last day and is an update, and a random date where we encountered the its
  -- previous crx_etag. We only use it to find the crx_etag again later.
  select
    crx_first_date1.crx_etag,
    crx_first_date1.extid,
    crx_first_date1.md as most_recent_update,
    crx_first_date2.md as some_date_with_previous_version
  from (
    select crx_etag,extid,min(date) as md
    from extension
    group by crx_etag
  ) crx_first_date1
  inner join (
    select extid,min(date) as md
    from extension
    group by crx_etag
  ) crx_first_date2
    on crx_first_date1.extid=crx_first_date2.extid
  where crx_first_date1.md>crx_first_date2.md
  and DATEDIFF(CURDATE(), crx_first_date1.md) = 0
  group by crx_first_date1.crx_etag
) crx_most_recent_and_prev
  inner join permission
    on crx_most_recent_and_prev.crx_etag=permission.crx_etag
  inner join extension extension_info
    on crx_most_recent_and_prev.extid=extension_info.extid
    and extension_info.date=most_recent_update
    and extension_info.crx_etag=crx_most_recent_and_prev.crx_etag
where permission not in (
  select permission
  from extension natural join permission
  where extid=extension_info.extid and date=some_date_with_previous_version
);
