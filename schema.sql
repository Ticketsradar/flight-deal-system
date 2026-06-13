-- schema.sql — Flight Deal System 資料庫 (Phase 2.5)
-- ===================================================
-- 點用:Supabase Dashboard → 左欄「SQL Editor」→「New query」→ 成段貼落去 → 撳「Run」。
-- 可以重複跑(全部 if not exists / drop policy if exists,唔會整爛已有資料)。
--
-- 設計:
--   cheap_flights — Stream A(scanner 每 route 每月最平);upsert key = (origin,destination,month)
--   error_fares   — Stream B(master 核實後嘅錯價);upsert key = source_url(同一帖更新狀態)
--   meta          — last_updated 時間戳等
--   RLS:三張枱開「公開只讀」(畀網站用 publishable key 讀);寫入只走 secret key(繞過 RLS)

-- ========== Stream A:平機票(每 route 每月最平)==========
create table if not exists cheap_flights (
    id            bigint generated always as identity primary key,
    origin        text not null,
    destination   text not null,
    region        text,
    depart_date   date,
    return_date   date,
    price_hkd     numeric,
    currency      text default 'HKD',
    airline       text,
    baggage       text,
    month         text,                          -- 'YYYY-MM'
    gflights_url  text,
    tripcom_url   text,
    periods       jsonb,                         -- top-3 平價時段 [{depart,return,price,airline,google_flights}]
    scanned_at    timestamptz default now(),
    constraint cheap_flights_route_month unique (origin, destination, month)
);
create index if not exists idx_cheap_origin_month on cheap_flights (origin, month);

-- ========== Stream B:錯價雷達 ==========
create table if not exists error_fares (
    id                 bigint generated always as identity primary key,
    origin             text not null,
    destination        text not null,
    airline            text,
    depart_date        date,
    return_date        date,
    claimed_price_hkd  numeric,
    verified_price_hkd numeric,                  -- nullable:unverified 時冇實價
    currency           text default 'HKD',
    status             text check (status in ('live', 'dead', 'unverified')),
    confidence         int,
    source_platform    text,
    source_url         text not null,
    gflights_url       text,
    tripcom_url        text,
    found_at           timestamptz default now(),
    verified_at        timestamptz default now(),
    constraint error_fares_source unique (source_url)
);
create index if not exists idx_error_status on error_fares (status, confidence desc);

-- ========== meta:時間戳 / 雜項 ==========
create table if not exists meta (
    key   text primary key,
    value text
);

-- ========== RLS:公開只讀(寫入只走 secret key)==========
alter table cheap_flights enable row level security;
alter table error_fares   enable row level security;
alter table meta          enable row level security;

drop policy if exists "public read cheap_flights" on cheap_flights;
create policy "public read cheap_flights" on cheap_flights for select using (true);

drop policy if exists "public read error_fares" on error_fares;
create policy "public read error_fares" on error_fares for select using (true);

drop policy if exists "public read meta" on meta;
create policy "public read meta" on meta for select using (true);
