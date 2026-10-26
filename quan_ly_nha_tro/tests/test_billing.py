from datetime import date

import pytest

from nhatro.billing import BillingError, so_ngay_o, tieu_thu, tinh_hoa_don


def test_tieu_thu():
    assert tieu_thu(100, 150, "điện") == 50
    assert tieu_thu(0, 0, "nước") == 0


def test_tieu_thu_moi_nho_hon_cu():
    with pytest.raises(BillingError):
        tieu_thu(150, 100, "điện")


def test_so_ngay_tinh_ca_hai_dau():
    assert so_ngay_o(date(2026, 10, 1), date(2026, 10, 1)) == 1
    assert so_ngay_o(date(2026, 10, 1), date(2026, 10, 10)) == 10


def test_hoa_don_thang():
    kq = tinh_hoa_don("thang", 3_000_000, 150_000, date(2026, 10, 1), date(2026, 10, 31),
                      1000, 1120, 50, 58, 3_500, 20_000, phi_khac=100_000)
    assert kq.tien_phong == 3_000_000
    assert kq.so_dien == 120 and kq.tien_dien == 420_000
    assert kq.so_nuoc == 8 and kq.tien_nuoc == 160_000
    assert kq.tong == 3_000_000 + 420_000 + 160_000 + 100_000


def test_hoa_don_ngay():
    kq = tinh_hoa_don("ngay", 3_000_000, 150_000, date(2026, 10, 1), date(2026, 10, 5),
                      10, 20, 1, 2, 3_500, 20_000)
    assert kq.so_ngay == 5
    assert kq.tien_phong == 750_000
    assert kq.tong == 750_000 + 35_000 + 20_000


def test_loai_sai():
    with pytest.raises(BillingError):
        tinh_hoa_don("tuan", 1, 1, date(2026, 1, 1), date(2026, 1, 2), 0, 0, 0, 0, 1, 1)
