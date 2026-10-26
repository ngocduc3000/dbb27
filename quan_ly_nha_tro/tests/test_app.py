import pytest

from nhatro.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def tao_phong(client, so="101"):
    return client.post("/phong/them", data=dict(
        so_phong=so, tang=1, dien_tich=20, gia_thang=3000000, gia_ngay=150000, so_nguoi_toi_da=2))


def test_tat_ca_trang_mo_duoc(client):
    tao_phong(client)
    for url in ["/", "/phong", "/phong/1", "/phong/1/sua", "/nguoi-thue", "/nguoi-thue/them",
                "/chi-so", "/hoa-don", "/hoa-don/tao", "/hoa-don/tao?phong_id=1", "/cau-hinh"]:
        assert client.get(url).status_code == 200, url


def test_trung_so_phong(client):
    tao_phong(client)
    r = tao_phong(client)
    assert r.status_code == 302
    assert "đã tồn tại" in client.get("/phong").get_data(as_text=True)


def test_luong_hoa_don_thang(client):
    tao_phong(client)
    client.post("/nguoi-thue/them", data=dict(phong_id=1, ho_ten="Nguyễn Văn A", ngay_vao="2026-09-01"))
    assert "Nguyễn Văn A" in client.get("/phong/1").get_data(as_text=True)

    client.post("/chi-so", data=dict(phong_id=1, ngay_ghi="2026-09-30", dien=1000, nuoc=50))
    client.post("/chi-so", data=dict(phong_id=1, ngay_ghi="2026-10-31", dien=1120, nuoc=58))

    # Điền sẵn chỉ số cũ/mới theo kỳ
    html = client.get("/hoa-don/tao?phong_id=1&loai=thang&tu_ngay=2026-10-01&den_ngay=2026-10-31").get_data(as_text=True)
    assert 'name="dien_cu" min="0" required value="1000"' in html
    assert 'name="dien_moi" min="0" required value="1120"' in html

    r = client.post("/hoa-don/tao", data=dict(
        phong_id=1, loai="thang", tu_ngay="2026-10-01", den_ngay="2026-10-31",
        dien_cu=1000, dien_moi=1120, nuoc_cu=50, nuoc_moi=58, phi_khac=100000))
    assert r.status_code == 302
    html = client.get(r.headers["Location"]).get_data(as_text=True)
    # 3.000.000 + 120*3.500 + 8*20.000 + 100.000 = 3.680.000
    assert "3.680.000" in html
    assert "Chưa thanh toán" in html

    client.post("/hoa-don/1/thanh-toan", data=dict(ngay_thanh_toan="2026-11-02"))
    assert "Đã thanh toán ngày 2026-11-02" in client.get("/hoa-don/1").get_data(as_text=True)


def test_hoa_don_ngay(client):
    tao_phong(client)
    r = client.post("/hoa-don/tao", data=dict(
        phong_id=1, loai="ngay", tu_ngay="2026-10-01", den_ngay="2026-10-05",
        dien_cu=10, dien_moi=20, nuoc_cu=1, nuoc_moi=2))
    html = client.get(r.headers["Location"]).get_data(as_text=True)
    # 5*150.000 + 10*3.500 + 1*20.000 = 805.000
    assert "805.000" in html and "5 ngày" in html


def test_chi_so_giam_bi_tu_choi(client):
    tao_phong(client)
    client.post("/chi-so", data=dict(phong_id=1, ngay_ghi="2026-10-01", dien=500, nuoc=20))
    client.post("/chi-so", data=dict(phong_id=1, ngay_ghi="2026-10-31", dien=400, nuoc=25))
    html = client.get("/chi-so").get_data(as_text=True)
    assert "nhỏ hơn lần ghi trước" in html
    assert "400" not in html


def test_tra_phong(client):
    tao_phong(client)
    client.post("/nguoi-thue/them", data=dict(phong_id=1, ho_ten="B", ngay_vao="2026-09-01"))
    client.post("/nguoi-thue/1/tra-phong", data=dict(ngay_ra="2026-10-15"))
    assert "Trống" in client.get("/phong").get_data(as_text=True)


def test_doi_don_gia(client):
    client.post("/cau-hinh", data=dict(don_gia_dien=4000, don_gia_nuoc=25000))
    html = client.get("/cau-hinh").get_data(as_text=True)
    assert 'value="4000"' in html and 'value="25000"' in html
