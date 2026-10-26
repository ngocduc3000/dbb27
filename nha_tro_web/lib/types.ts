export interface Phong {
  id: number;
  so_phong: string;
  tang: number;
  dien_tich: number;
  gia_thang: number;
  gia_ngay: number;
  so_nguoi_toi_da: number;
  ghi_chu: string;
}

export interface NguoiThue {
  id: number;
  phong_id: number;
  ho_ten: string;
  cccd: string;
  sdt: string;
  ngay_sinh: string | null;
  que_quan: string;
  ngay_vao: string;
  ngay_ra: string | null;
  ghi_chu: string;
}

export interface ChiSo {
  id: number;
  phong_id: number;
  ngay_ghi: string;
  dien: number;
  nuoc: number;
}

export interface HoaDon {
  id: number;
  phong_id: number;
  loai: "thang" | "ngay";
  tu_ngay: string;
  den_ngay: string;
  so_ngay: number;
  dien_cu: number;
  dien_moi: number;
  nuoc_cu: number;
  nuoc_moi: number;
  don_gia_dien: number;
  don_gia_nuoc: number;
  tien_phong: number;
  tien_dien: number;
  tien_nuoc: number;
  phi_khac: number;
  tong: number;
  da_thanh_toan: boolean;
  ngay_thanh_toan: string | null;
  ghi_chu: string;
}

export type HoaDonCoPhong = HoaDon & { phong: { so_phong: string } | null };
