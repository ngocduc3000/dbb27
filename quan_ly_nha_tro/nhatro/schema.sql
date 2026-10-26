-- Cấu hình chung (đơn giá điện, nước)
CREATE TABLE IF NOT EXISTS cau_hinh (
    khoa    TEXT PRIMARY KEY,
    gia_tri TEXT NOT NULL
);

-- Phòng trọ
CREATE TABLE IF NOT EXISTS phong (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    so_phong    TEXT    NOT NULL UNIQUE,
    tang        INTEGER NOT NULL DEFAULT 1,
    dien_tich   REAL    NOT NULL DEFAULT 0,      -- m2
    gia_thang   INTEGER NOT NULL DEFAULT 0,      -- VNĐ / tháng
    gia_ngay    INTEGER NOT NULL DEFAULT 0,      -- VNĐ / ngày
    so_nguoi_toi_da INTEGER NOT NULL DEFAULT 2,
    ghi_chu     TEXT    NOT NULL DEFAULT ''
);

-- Người ở trọ
CREATE TABLE IF NOT EXISTS nguoi_thue (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    phong_id  INTEGER NOT NULL REFERENCES phong(id),
    ho_ten    TEXT    NOT NULL,
    cccd      TEXT    NOT NULL DEFAULT '',
    sdt       TEXT    NOT NULL DEFAULT '',
    ngay_sinh TEXT    NOT NULL DEFAULT '',
    que_quan  TEXT    NOT NULL DEFAULT '',
    ngay_vao  TEXT    NOT NULL,                  -- YYYY-MM-DD
    ngay_ra   TEXT,                              -- NULL = đang ở
    ghi_chu   TEXT    NOT NULL DEFAULT ''
);

-- Chỉ số điện nước mỗi lần ghi
CREATE TABLE IF NOT EXISTS chi_so (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    phong_id  INTEGER NOT NULL REFERENCES phong(id),
    ngay_ghi  TEXT    NOT NULL,                  -- YYYY-MM-DD
    dien      INTEGER NOT NULL,                  -- kWh trên đồng hồ
    nuoc      INTEGER NOT NULL,                  -- m3 trên đồng hồ
    UNIQUE (phong_id, ngay_ghi)
);

-- Hóa đơn (theo tháng hoặc theo ngày)
CREATE TABLE IF NOT EXISTS hoa_don (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phong_id    INTEGER NOT NULL REFERENCES phong(id),
    loai        TEXT    NOT NULL CHECK (loai IN ('thang', 'ngay')),
    tu_ngay     TEXT    NOT NULL,
    den_ngay    TEXT    NOT NULL,
    so_ngay     INTEGER NOT NULL,
    dien_cu     INTEGER NOT NULL,
    dien_moi    INTEGER NOT NULL,
    nuoc_cu     INTEGER NOT NULL,
    nuoc_moi    INTEGER NOT NULL,
    don_gia_dien INTEGER NOT NULL,
    don_gia_nuoc INTEGER NOT NULL,
    tien_phong  INTEGER NOT NULL,
    tien_dien   INTEGER NOT NULL,
    tien_nuoc   INTEGER NOT NULL,
    phi_khac    INTEGER NOT NULL DEFAULT 0,
    tong        INTEGER NOT NULL,
    da_thanh_toan INTEGER NOT NULL DEFAULT 0,
    ngay_thanh_toan TEXT,
    ghi_chu     TEXT    NOT NULL DEFAULT '',
    ngay_tao    TEXT    NOT NULL DEFAULT (date('now', 'localtime'))
);

INSERT OR IGNORE INTO cau_hinh (khoa, gia_tri) VALUES ('don_gia_dien', '3500');
INSERT OR IGNORE INTO cau_hinh (khoa, gia_tri) VALUES ('don_gia_nuoc', '20000');
