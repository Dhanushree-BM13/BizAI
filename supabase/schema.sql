-- =====================================================================
-- BizAI database schema
-- Run this first in the Supabase SQL Editor, then run seed.sql.
-- Safe to run again: every statement checks before it creates.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Companies: one row per company
-- ---------------------------------------------------------------------
create table if not exists public.companies (
  id          bigint generated always as identity primary key,
  name        text        not null unique check (length(trim(name)) > 0),
  industry    text        not null default 'Uncategorised',
  created_at  timestamptz not null default now()
);

comment on table  public.companies          is 'Companies tracked by BizAI.';
comment on column public.companies.industry is 'Sector, shown under the company name on the dashboard.';

-- ---------------------------------------------------------------------
-- 2. Monthly financials: one row per company per month
-- ---------------------------------------------------------------------
create table if not exists public.monthly_financials (
  id               bigint generated always as identity primary key,
  company_id       bigint        not null references public.companies (id) on delete cascade,
  month            date          not null check (month = date_trunc('month', month)::date),
  revenue          numeric(14,2) not null check (revenue > 0),
  expenses         numeric(14,2) not null check (expenses >= 0),
  project_success  numeric(5,2)  check (project_success between 0 and 100),
  created_at       timestamptz   not null default now(),
  unique (company_id, month)  -- also serves as the index for looking up a company's months
);

create index if not exists monthly_financials_month_idx on public.monthly_financials (month);

comment on table  public.monthly_financials                 is 'Revenue and expenses per company per month, in rupees crore.';
comment on column public.monthly_financials.month           is 'First day of the month the figures cover.';
comment on column public.monthly_financials.project_success is 'Share of projects delivered successfully that month, 0 to 100. Optional.';

-- ---------------------------------------------------------------------
-- 3. View the app reads: companies joined to their months
-- security_invoker makes the view obey the row level security below.
-- ---------------------------------------------------------------------
create or replace view public.company_financials
with (security_invoker = true) as
select f.id,
       c.name     as company,
       c.industry,
       f.month    as date,
       f.revenue,
       f.expenses,
       f.project_success
from public.monthly_financials f
join public.companies c on c.id = f.company_id;

comment on view public.company_financials is 'Flat view of every company month, read by the BizAI dashboard.';

-- ---------------------------------------------------------------------
-- 4. Security: only signed-in users may read; nobody may write through the API.
-- Accounts come from Supabase Auth (the app's login page). Add or change data
-- in the Supabase Table Editor or SQL Editor.
-- ---------------------------------------------------------------------
alter table public.companies          enable row level security;
alter table public.monthly_financials enable row level security;

drop policy if exists "Anyone can read companies" on public.companies;
drop policy if exists "Signed-in users can read companies" on public.companies;
create policy "Signed-in users can read companies"
  on public.companies for select to authenticated using (true);

drop policy if exists "Anyone can read monthly financials" on public.monthly_financials;
drop policy if exists "Signed-in users can read monthly financials" on public.monthly_financials;
create policy "Signed-in users can read monthly financials"
  on public.monthly_financials for select to authenticated using (true);

revoke select on public.company_financials from anon;
grant select on public.company_financials to authenticated;

-- ---------------------------------------------------------------------
-- 5. Realtime: tell the dashboard when figures change
-- ---------------------------------------------------------------------
do $$ begin
  alter publication supabase_realtime add table public.companies;
exception when duplicate_object then null;
end $$;

do $$ begin
  alter publication supabase_realtime add table public.monthly_financials;
exception when duplicate_object then null;
end $$;
