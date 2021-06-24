with deduped_parts as (
    select  i.set_num set_num,
            s.name set_name,
            ip.part_num as part_num,
            ip.color_id as color_id,
            max(ip.quantity) quantity
    from    inventories i
    join    inventory_parts ip on (i.id = ip.inventory_id)
    join    sets s on (s.set_num = i.set_num)
    group by i.set_num, s.name, ip.part_num, ip.color_id
)
select  dp.set_num as set_num,
        dp.set_name as set_name,
        dp.part_num as part_num,
        sum(dp.quantity) quantity
from    deduped_parts dp
group by dp.set_num, dp.set_name, dp.part_num
order by set_num desc