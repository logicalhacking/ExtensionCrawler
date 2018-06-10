select *
from (
  select 
    ext1.extid as e1, 
    ext1.date as d1, 
    crx1.path as p1, 
    ext2.extid as e2, 
    ext2.date as d2, 
    crx2.path as p2, 
    BIT_COUNT((cast(crx1.simhash as unsigned int)) ^ (cast(crx2.simhash as unsigned int))) as dist 
  from (((extension as ext1 inner join crxfile as crx1 using (crx_etag)))
    inner join ((extension as ext2 inner join crxfile as crx2 using (crx_etag))))
  where 
    crx1.simhash IS NOT NULL and 
    crx2.simhash IS NOT NULL and 
    crx1.md5 <> crx2.md5 
    and (crx1.crx_etag, crx1.path) < (crx2.crx_etag, crx2.path) 
) as foo
where
  dist < 4
group by e1, e1, p1, e2, d2, p2
order by dist;
