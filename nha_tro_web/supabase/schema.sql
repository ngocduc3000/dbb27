-- Schema quản lý nhà trọ cho Supabase.
-- Chạy 1 lần trong Supabase Dashboard → SQL Editor → New query → dán toàn bộ → Run.
-- Mỗi tài khoản đăng nhập (chủ trọ) chỉ thấy dữ liệu của mình (Row Level Security).

-- Đơn giá điện nước, mỗi chủ trọ 1 dòng
create table if not exists public.cau_hinh (
  owner_id      uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  don_gia_dien  integer not null default 3500  check (don_gia_dien >= 0),
  don_gia_nuoc  integer not null default 20000 check (don_gia_nuoc >= 0)
);

-- Phòng trọ
create table if not exists public.phong (
  id              bigint generated always as identity primary key,
  owner_id        uuid not null default auth.uid() references auth.users (id) on delete cascade,
  so_phong        text not null check (length(trim(so_phong)) > 0),
  tang            integer not null default 1,
  dien_tich       numeric(6,1) not null default 0 check (dien_tich >= 0),
  gia_thang       integer not null default 0 check (gia_thang >= 0),
  gia_ngay        integer not null default 0 check (gia_ngay >= 0),
  so_nguoi_toi_da integer not null default 2 check (so_nguoi_toi_da >= 1),
  ghi_chu         text not null default '',
  unique (owner_id, so_phong)
);

-- Người ở trọ
create table if not exists public.nguoi_thue (
  id        bigint generated always as identity primary key,
  owner_id  uuid not null default auth.uid() references auth.users (id) on delete cascade,
  phong_id  bigint not null references public.phong (id) on delete restrict,
  ho_ten    text not null check (length(trim(ho_ten)) > 0),
  cccd      text not null default '',
  sdt       text not null default '',
  ngay_sinh date,
  que_quan  text not null default '',
  ngay_vao  date not null,
  ngay_ra   date,                                  -- null = đang ở
  ghi_chu   text not null default '',
  check (ngay_ra is null or ngay_ra >= ngay_vao)
);

-- Chỉ số đồng hồ điện nước mỗi lần ghi
create table if not exists public.chi_so (
  id        bigint generated always as identity primary key,
  owner_id  uuid not null default auth.uid() references auth.users (id) on delete cascade,
  phong_id  bigint not null references public.phong (id) on delete restrict,
  ngay_ghi  date not null,
  dien      integer not null check (dien >= 0),    -- kWh
  nuoc      integer not null check (nuoc >= 0),    -- m3
  unique (phong_id, ngay_ghi)
);

-- Hóa đơn theo tháng hoặc theo ngày
create table if not exists public.hoa_don (
  id              bigint generated always as identity primary key,
  owner_id        uuid not null default auth.uid() references auth.users (id) on delete cascade,
  phong_id        bigint not null references public.phong (id) on delete restrict,
  loai            text not null check (loai in ('thang', 'ngay')),
  tu_ngay         date not null,
  den_ngay        date not null,
  so_ngay         integer not null check (so_ngay >= 1),
  dien_cu         integer not null check (dien_cu >= 0),
  dien_moi        integer not null,
  nuoc_cu         integer not null check (nuoc_cu >= 0),
  nuoc_moi        integer not null,
  don_gia_dien    integer not null check (don_gia_dien >= 0),
  don_gia_nuoc    integer not null check (don_gia_nuoc >= 0),
  tien_phong      bigint not null check (tien_phong >= 0),
  tien_dien       bigint not null check (tien_dien >= 0),
  tien_nuoc       bigint not null check (tien_nuoc >= 0),
  phi_khac        bigint not null default 0 check (phi_khac >= 0),
  tong            bigint not null,
  da_thanh_toan   boolean not null default false,
  ngay_thanh_toan date,
  ghi_chu         text not null default '',
  created_at      timestamptz not null default now(),
  check (den_ngay >= tu_ngay),
  check (dien_moi >= dien_cu),
  check (nuoc_moi >= nuoc_cu),
  check (tong = tien_phong + tien_dien + tien_nuoc + phi_khac)
);

create index if not exists nguoi_thue_phong_idx on public.nguoi_thue (phong_id);
create index if not exists chi_so_phong_ngay_idx on public.chi_so (phong_id, ngay_ghi desc);
create index if not exists hoa_don_phong_idx on public.hoa_don (phong_id, tu_ngay desc);

-- Không cho gắn bản ghi vào phòng của chủ trọ khác
create or replace function public.kiem_tra_phong_cua_minh() returns trigger
language plpgsql security invoker as $$
begin
  if not exists (select 1 from public.phong p where p.id = new.phong_id and p.owner_id = new.owner_id) then
    raise exception 'Phòng không tồn tại';
  end if;
  return new;
end $$;

drop trigger if exists nguoi_thue_phong_chk on public.nguoi_thue;
create trigger nguoi_thue_phong_chk before insert or update on public.nguoi_thue
  for each row execute function public.kiem_tra_phong_cua_minh();
drop trigger if exists chi_so_phong_chk on public.chi_so;
create trigger chi_so_phong_chk before insert or update on public.chi_so
  for each row execute function public.kiem_tra_phong_cua_minh();
drop trigger if exists hoa_don_phong_chk on public.hoa_don;
create trigger hoa_don_phong_chk before insert or update on public.hoa_don
  for each row execute function public.kiem_tra_phong_cua_minh();

-- Row Level Security: chỉ đọc/ghi dữ liệu của chính mình
do $$
declare t text;
begin
  foreach t in array array['cau_hinh', 'phong', 'nguoi_thue', 'chi_so', 'hoa_don'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists chu_tro on public.%I', t);
    execute format(
      'create policy chu_tro on public.%I for all to authenticated '
      'using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()))', t);
  end loop;
end $$;
