select extid as e,name,min(date),permission
from extension natural join crx natural join permission
-- Ensure we have at least two different crx files, otherwise we have an empty permission
-- set in the previous where clause
where (
  select count(*)
  from (
    select *
    from extension
    where crx_etag not null
    and extid=e
    -- Ensure we have seen two different crx_etags of this extensions within the last two runs
    and date in (
      select date
      from extension
      where extid=e
      order by date desc
      limit 2
    )
    group by extid,crx_etag
    -- order by date desc
    limit 2
  )
) = 2
-- Select newest crx file
and crx_etag=(
  select crx_etag
  from extension
  where crx_etag not null
  and extid=e
  group by extid,crx_etag
  order by date desc
  limit 1
)
-- Ensure permission is not present in previous crx
and permission not in (
  select permission
  from permission
  -- Select the second newest crx that we have
  where crx_etag=(
    select crx_etag
    from extension
    where crx_etag not null
    and extid=e
    group by extid,crx_etag
    order by date desc
    limit 1
    offset 1
  )
)
group by extid,permission;
