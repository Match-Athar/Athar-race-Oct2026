-- Athar (أثر) — database schema for a live version (Supabase / any Postgres 14+).
-- Load the CSVs written by `python run.py ... --csv` into the three base tables.
--
-- Security model:
--   * Base tables hold AMOUNTS → only signed-in admins (RLS, no anon policy).
--   * public_board and public_top_users expose percentages, flags and names only → readable by anon.
--     They are owner-rights views on purpose (they read the protected tables for the public page).

create table if not exists fx_rates (
  country  text primary key,
  to_sar   numeric not null
);
insert into fx_rates (country, to_sar) values
  ('KSA', 1.0), ('UAE', 1.02), ('Oman', 9.75), ('Kuwait', 12.30), ('Bahrain', 10.0), ('Qatar', 1.03)
on conflict (country) do update set to_sar = excluded.to_sar;

create table if not exists targets (
  month        date not null,          -- first day of the month
  store        text not null,
  country      text not null references fx_rates(country),
  region       text,
  city         text,
  target_local numeric not null,       -- in the country's own currency
  primary key (month, store)
);

create table if not exists daily_sales (
  sale_date   date not null,
  store       text not null,
  sales_local numeric not null,        -- that day's sales, own currency
  primary key (sale_date, store)
);

create table if not exists user_sales_mtd (
  asof        date not null,
  store       text not null,
  pos_user    text not null,
  is_employee boolean not null,        -- personal account like 1238-Name / Name-6563
  sales_local numeric not null,        -- month-to-date
  primary key (asof, store, pos_user)
);

alter table fx_rates       enable row level security;
alter table targets        enable row level security;
alter table daily_sales    enable row level security;
alter table user_sales_mtd enable row level security;
-- admins (any signed-in user here; narrow it to your admin emails/roles in production)
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    create policy admin_all_fx  on fx_rates       for all to authenticated using (true) with check (true);
    create policy admin_all_tg  on targets        for all to authenticated using (true) with check (true);
    create policy admin_all_ds  on daily_sales    for all to authenticated using (true) with check (true);
    create policy admin_all_us  on user_sales_mtd for all to authenticated using (true) with check (true);
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- Month-to-date per branch (INTERNAL: contains amounts)
create or replace view branch_mtd as
with latest as (
  select date_trunc('month', sale_date)::date as month, max(sale_date) as asof
  from daily_sales group by 1
),
sums as (
  select l.month, l.asof, d.store,
         sum(d.sales_local)                                           as sales_local,
         sum(d.sales_local) filter (where d.sale_date < l.asof)       as sales_prev
  from daily_sales d
  join latest l on date_trunc('month', d.sale_date)::date = l.month
  group by 1, 2, 3
)
select t.month, l.asof, t.store, t.country, t.region, t.city, t.target_local,
       coalesce(s.sales_local, 0)                                     as sales_local,
       coalesce(s.sales_local, 0) * f.to_sar                          as sales_sar,
       coalesce(s.sales_local, 0) / nullif(t.target_local, 0)         as achievement,
       coalesce(s.sales_prev, 0)  / nullif(t.target_local, 0)         as achievement_prev,
       extract(day from l.asof)::numeric
         / extract(day from (t.month + interval '1 month - 1 day'))   as elapsed_frac
from targets t
join latest l      on l.month = t.month
join fx_rates f    on f.country = t.country
left join sums s   on s.month = t.month and s.store = t.store
where t.store <> 'EXBUAE';

-- ---------------------------------------------------------------------------
-- PUBLIC: percentages and a car-eligibility flag only (no amounts)
create or replace view public_board as
select month, asof, store, country, city,
       round(achievement, 4)                                  as achievement,
       round(achievement - achievement_prev, 4)               as change_today,
       round(achievement / nullif(elapsed_frac, 0), 3)        as projected,
       (sales_sar / nullif(elapsed_frac, 0) >= 300000)        as car_eligible,   -- projected ≥ 300k SAR
       rank() over (partition by month order by achievement desc)      as rank_now,
       rank() over (partition by month order by achievement_prev desc) as rank_prev
from branch_mtd;

-- PUBLIC: top 3 personal accounts per branch, as "Name (1234)", no amounts
create or replace view public_top_users as
with latest as (select max(asof) as asof from user_sales_mtd),
ranked as (
  select u.store, u.pos_user,
         row_number() over (partition by u.store order by u.sales_local desc) as pos
  from user_sales_mtd u join latest l on u.asof = l.asof
  where u.is_employee
)
select store, pos,
       case when pos_user ~ '^[0-9]{3,}\s*-'
            then regexp_replace(trim(pos_user), '^([0-9]{3,})\s*-\s*(.+)$', '\2 (\1)')
            else regexp_replace(trim(pos_user), '^(.+?)\s*-\s*([0-9]{3,})$', '\1 (\2)')
       end as display_name
from ranked where pos <= 3;

do $$ begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    grant select on public_board, public_top_users to anon, authenticated;
    grant select on branch_mtd to authenticated;
  end if;
end $$;
