-- ---------------------------------------------------------------------
-- BizAI demo data: 40 invented companies, 5 years of months.
-- The rows are computed here from each company's parameters, using the
-- same formula as generate_data.py. Safe to run again.
-- ---------------------------------------------------------------------

-- Repeatable random numbers from an MD5 hash (temporary: gone after this run)
create or replace function pg_temp.uniform(company text, t int, slot int) returns double precision
language sql immutable as $$
  select (('x' || lpad(substr(md5(company || ':' || t || ':' || slot), 1, 7), 8, '0'))::bit(32)::int / 268435456.0)::double precision
$$;

create or replace function pg_temp.normal(company text, t int, slot int) returns double precision
language sql immutable as $$
  select (pg_temp.uniform(company, t, slot) + pg_temp.uniform(company, t, slot + 1)
        + pg_temp.uniform(company, t, slot + 2) + pg_temp.uniform(company, t, slot + 3) - 2) * sqrt(3)
$$;

-- name, industry, starting revenue (Rs crore), monthly growth, seasonal swing, profit margin, monthly margin change
with params (name, industry, start_revenue, growth, swing, margin, drift) as (values
  ('Aravali Energy', 'Energy', 7200, 0.006, 0.05, 0.15, 0.0),
  ('Nilgiri Infotech', 'IT Services', 1950, 0.01, 0.03, 0.24, 0.0),
  ('Kaveri Systems', 'IT Services', 1300, 0.008, 0.03, 0.21, -0.001),
  ('Sahyadri Cloud', 'Technology', 4500, 0.015, 0.02, 0.28, 0.0),
  ('Surya Kiran Solar', 'Renewable Energy', 11.4, 0.018, 0.08, 0.17, 0.0),
  ('Vindhya Consulting', 'Consulting', 820, -0.004, 0.04, 0.12, -0.001),
  ('Konkan Retail', 'Retail', 640, 0.005, 0.12, 0.09, 0.0),
  ('Godavari Pharma', 'Pharmaceuticals', 2100, 0.009, 0.03, 0.22, 0.0),
  ('Deccan Motors', 'Automobile', 5600, 0.004, 0.07, 0.11, 0.0),
  ('Malabar Foods', 'FMCG', 1500, 0.007, 0.06, 0.14, 0.0),
  ('Ganga Textiles', 'Textiles', 430, -0.002, 0.09, 0.08, -0.0008),
  ('Himadri Cement', 'Cement', 3200, 0.005, 0.1, 0.16, 0.0),
  ('Narmada Finserv', 'Financial Services', 2700, 0.012, 0.02, 0.26, 0.0),
  ('Thar Logistics', 'Logistics', 960, 0.008, 0.05, 0.1, 0.0005),
  ('Chenab Telecom', 'Telecom', 6400, 0.003, 0.02, 0.13, -0.0005),
  ('Brahmaputra Steel', 'Steel', 8900, 0.004, 0.06, 0.12, -0.0004),
  ('Kanchenjunga Hotels', 'Hospitality', 380, 0.011, 0.18, 0.18, 0.0),
  ('Mahanadi Power', 'Power Utilities', 5200, 0.005, 0.07, 0.19, 0.0),
  ('Tapti Chemicals', 'Chemicals', 1750, 0.006, 0.04, 0.15, -0.0006),
  ('Satpura Agritech', 'Agriculture', 290, 0.013, 0.2, 0.11, 0.0),
  ('Kaziranga Airways', 'Aviation', 4100, 0.009, 0.14, 0.05, 0.0004),
  ('Palghat Paints', 'Paints', 1150, 0.008, 0.08, 0.17, 0.0),
  ('Shivalik Realty', 'Real Estate', 960, 0.003, 0.1, 0.21, -0.0012),
  ('Mysuru Silks', 'Textiles', 145, 0.006, 0.15, 0.13, 0.0),
  ('Indus Bank Tech', 'Fintech', 520, 0.02, 0.02, 0.09, 0.002),
  ('Coromandel Fertilisers', 'Fertilisers', 2400, 0.004, 0.16, 0.1, 0.0),
  ('Nalanda EdTech', 'Education', 210, 0.016, 0.12, 0.14, -0.0015),
  ('Sundarban Seafoods', 'Food Exports', 330, 0.007, 0.11, 0.08, 0.0),
  ('Ajanta Healthcare', 'Hospitals', 1350, 0.01, 0.03, 0.16, 0.0),
  ('Garuda Aerospace', 'Defence', 1900, 0.012, 0.04, 0.2, 0.0),
  ('Chambal Tyres', 'Auto Components', 1600, 0.005, 0.06, 0.11, 0.0),
  ('Lonavala Media', 'Media', 470, -0.006, 0.08, 0.1, -0.001),
  ('Kutch Salt Works', 'Commodities', 95, 0.004, 0.13, 0.07, 0.0),
  ('Vaigai Electronics', 'Electronics', 2850, 0.014, 0.05, 0.09, 0.0006),
  ('Hampi Gaming', 'Gaming', 120, 0.022, 0.06, 0.24, -0.002),
  ('Rann Wind Energy', 'Renewable Energy', 640, 0.017, 0.12, 0.26, 0.0),
  ('Periyar Rubber', 'Rubber', 410, -0.003, 0.09, 0.09, -0.0005),
  ('Darjeeling Tea Estates', 'Plantations', 180, 0.002, 0.25, 0.12, 0.0),
  ('Bengaluru Biotech', 'Biotechnology', 760, 0.015, 0.03, 0.18, 0.0),
  ('Mumbai Insure', 'Insurance', 3600, 0.009, 0.02, 0.14, 0.0)
),
saved_companies as (
  insert into public.companies (name, industry)
  select name, industry from params
  on conflict (name) do update set industry = excluded.industry
  returning id, name
)
insert into public.monthly_financials (company_id, month, revenue, expenses, project_success)
select c.id, d.month,
       round((r.revenue * case when x.unusual and not x.cost_overrun then 0.86 + 0.04 * x.size else 1 end)::numeric, 2),
       round((x.expenses * case when x.unusual and x.cost_overrun then 1.12 + 0.08 * x.size else 1 end)::numeric, 2),
       round((x.success - case when x.unusual then 12 + 6 * x.size else 0 end)::numeric, 1)
from params p
join saved_companies c on c.name = p.name
cross join generate_series(0, 59) as t
cross join lateral (select (date '2021-11-01' + t * interval '1 month')::date as month) d
cross join lateral (
  select p.start_revenue * power(1 + p.growth, t)
         * (1 + p.swing * sin(2 * pi() * (extract(month from d.month)::int - 3) / 12))
         * (1 + 0.012 * pg_temp.normal(p.name, t, 0)) as revenue
) r
cross join lateral (
  select r.revenue * (1 - p.margin - p.drift * t) * (1 + 0.008 * pg_temp.normal(p.name, t, 4)) as expenses,
         least(98, greatest(82, 91 + 2.5 * pg_temp.normal(p.name, t, 8)))       as success,
         t >= 3 and pg_temp.uniform(p.name, t, 12) < 3.0 / 57                     as unusual,
         pg_temp.uniform(p.name, t, 13) < 0.5                                     as cost_overrun,
         pg_temp.uniform(p.name, t, 14)                                           as size
) x
on conflict (company_id, month) do update
  set revenue = excluded.revenue, expenses = excluded.expenses, project_success = excluded.project_success;
