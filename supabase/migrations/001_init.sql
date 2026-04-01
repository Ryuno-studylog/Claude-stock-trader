-- ユーザープロフィール（auth.users を拡張）
create table public.profiles (
  id          uuid references auth.users on delete cascade primary key,
  credits     integer      not null default 1,   -- 無料枠1回
  plan        text         not null default 'free', -- 'free' | 'monthly'
  language    text         not null default 'ja',
  created_at  timestamptz  not null default now(),
  updated_at  timestamptz  not null default now()
);

alter table public.profiles enable row level security;
create policy "own_profile_select" on public.profiles for select using (auth.uid() = id);
create policy "own_profile_update" on public.profiles for update using (auth.uid() = id);

-- ユーザーごとの設定
create table public.user_settings (
  user_id            uuid references auth.users on delete cascade primary key,
  stock_universe     jsonb,
  screening_defaults jsonb,
  plan_defaults      jsonb,
  updated_at         timestamptz not null default now()
);

alter table public.user_settings enable row level security;
create policy "own_settings" on public.user_settings for all using (auth.uid() = user_id);

-- 生成履歴
create table public.plan_history (
  id               uuid        primary key default gen_random_uuid(),
  user_id          uuid        references auth.users on delete cascade,
  created_at       timestamptz not null default now(),
  vix              float,
  vix_level        text,
  budget           integer,
  holding_period   text,
  risk_tolerance   text,
  review_note      text,
  screened_stocks  jsonb,
  plan_text        text
);

alter table public.plan_history enable row level security;
create policy "own_history" on public.plan_history for all using (auth.uid() = user_id);

-- 新規ユーザー作成時に profile を自動生成
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id) values (new.id);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
