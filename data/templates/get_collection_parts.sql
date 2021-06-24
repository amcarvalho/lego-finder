with deduped_parts as (
    select  ip.part_num as part_num,
            ip.color_id as color_id,
            max(ip.quantity) quantity
    from    inventories i
    join    inventory_parts ip on (i.id = ip.inventory_id)
    where   set_num in ({{ set_num }})
    group by ip.part_num, ip.color_id
),
sum_parts as (
    select  dp.part_num as part_num,
            sum(dp.quantity) quantity
    from    deduped_parts dp
    group by dp.part_num
)
select  sp.part_num,
        p.name,
        quantity
from    sum_parts sp
join    parts p on (sp.part_num = p.part_num)