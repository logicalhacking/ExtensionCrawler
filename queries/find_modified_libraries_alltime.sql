select * from (
  select 
    cdnjs.path as p1, 
    cdnjs.typ as t1, 
    extid as e2, 
    date as d2, 
    crxfile.path as p2, 
    crxfile.typ as t2, 
    BIT_COUNT((cast(cdnjs.simhash as unsigned int)) ^ (cast(crxfile.simhash as unsigned int))) as dist 
  from extensions.cdnjs inner join (extension inner join crxfile using (crx_etag)) 
  where 
    crxfile.simhash IS NOT NULL
) as foo
where
  dist < 4
group by
  p1, e2, d2, p2
order by dist;
