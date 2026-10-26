"""Tính tiền phòng / điện / nước. Hàm thuần, không đụng database."""
from dataclasses import dataclass
from datetime import date


class BillingError(ValueError):
    pass


@dataclass
class KetQuaHoaDon:
    loai: str            # "thang" hoặc "ngay"
    so_ngay: int         # số ngày ở (chỉ dùng cho loại "ngay")
    tien_phong: int
    so_dien: int         # kWh tiêu thụ
    tien_dien: int
    so_nuoc: int         # m3 tiêu thụ
    tien_nuoc: int
    phi_khac: int
    tong: int


def tieu_thu(chi_so_cu: int, chi_so_moi: int, ten: str) -> int:
    """Số tiêu thụ = mới - cũ. Báo lỗi nếu chỉ số âm hoặc mới < cũ."""
    if chi_so_cu < 0 or chi_so_moi < 0:
        raise BillingError(f"Chỉ số {ten} không được âm")
    if chi_so_moi < chi_so_cu:
        raise BillingError(f"Chỉ số {ten} mới ({chi_so_moi}) nhỏ hơn chỉ số cũ ({chi_so_cu})")
    return chi_so_moi - chi_so_cu


def so_ngay_o(tu_ngay: date, den_ngay: date) -> int:
    """Số ngày tính tiền, tính cả ngày đầu và ngày cuối."""
    if den_ngay < tu_ngay:
        raise BillingError("Ngày kết thúc nhỏ hơn ngày bắt đầu")
    return (den_ngay - tu_ngay).days + 1


def tinh_hoa_don(
    loai: str,
    gia_thang: int,
    gia_ngay: int,
    tu_ngay: date,
    den_ngay: date,
    dien_cu: int,
    dien_moi: int,
    nuoc_cu: int,
    nuoc_moi: int,
    don_gia_dien: int,
    don_gia_nuoc: int,
    phi_khac: int = 0,
) -> KetQuaHoaDon:
    if loai not in ("thang", "ngay"):
        raise BillingError("Loại hóa đơn phải là 'thang' hoặc 'ngay'")
    if min(gia_thang, gia_ngay, don_gia_dien, don_gia_nuoc, phi_khac) < 0:
        raise BillingError("Giá / phí không được âm")

    n = so_ngay_o(tu_ngay, den_ngay)
    tien_phong = gia_thang if loai == "thang" else gia_ngay * n

    so_dien = tieu_thu(dien_cu, dien_moi, "điện")
    so_nuoc = tieu_thu(nuoc_cu, nuoc_moi, "nước")
    tien_dien = so_dien * don_gia_dien
    tien_nuoc = so_nuoc * don_gia_nuoc

    return KetQuaHoaDon(
        loai=loai,
        so_ngay=n,
        tien_phong=tien_phong,
        so_dien=so_dien,
        tien_dien=tien_dien,
        so_nuoc=so_nuoc,
        tien_nuoc=tien_nuoc,
        phi_khac=phi_khac,
        tong=tien_phong + tien_dien + tien_nuoc + phi_khac,
    )
