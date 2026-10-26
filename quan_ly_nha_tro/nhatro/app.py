"""Web app quản lý nhà trọ (Flask + SQLite)."""
import calendar
import os
from datetime import date

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for

from . import db
from .billing import BillingError, tinh_hoa_don

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _int(name: str, default: int = 0) -> int:
    v = request.form.get(name, "").strip().replace(".", "").replace(",", "")
    if v == "":
        return default
    try:
        return int(v)
    except ValueError:
        raise BillingError(f"Giá trị '{name}' không phải số: {v}")


def _date(name: str) -> date:
    v = request.form.get(name, "").strip()
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise BillingError(f"Ngày '{name}' không hợp lệ: {v}")


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
    app.config["SECRET_KEY"] = os.environ.get("NHATRO_SECRET", "doi-khoa-nay-khi-trien-khai")
    app.config["DB_PATH"] = db_path or os.environ.get("NHATRO_DB", os.path.join(BASE_DIR, "nhatro.db"))

    with app.app_context():
        conn = db.connect(app.config["DB_PATH"])
        db.init_db(conn)
        conn.close()

    def get_db():
        if "db" not in g:
            g.db = db.connect(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.template_filter("vnd")
    def vnd(n):
        return f"{int(n or 0):,}".replace(",", ".")

    @app.errorhandler(BillingError)
    def billing_error(e):
        flash(str(e), "error")
        return redirect(request.referrer or url_for("index"))

    # ---------- Tổng quan ----------
    @app.route("/")
    def index():
        conn = get_db()
        phongs = db.danh_sach_phong(conn)
        no = conn.execute(
            "SELECT COUNT(*) AS so, COALESCE(SUM(tong), 0) AS tien FROM hoa_don WHERE da_thanh_toan = 0"
        ).fetchone()
        thang = date.today().strftime("%Y-%m")
        thu = conn.execute(
            "SELECT COALESCE(SUM(tong), 0) FROM hoa_don "
            "WHERE da_thanh_toan = 1 AND substr(ngay_thanh_toan, 1, 7) = ?", (thang,)
        ).fetchone()[0]
        return render_template("index.html", phongs=phongs, no=no, thu=thu, thang=thang)

    # ---------- Phòng ----------
    @app.route("/phong")
    def phong_list():
        return render_template("phong_list.html", phongs=db.danh_sach_phong(get_db()))

    @app.route("/phong/them", methods=["GET", "POST"])
    @app.route("/phong/<int:pid>/sua", methods=["GET", "POST"])
    def phong_form(pid=None):
        conn = get_db()
        phong = None
        if pid is not None:
            phong = conn.execute("SELECT * FROM phong WHERE id = ?", (pid,)).fetchone() or abort(404)
        if request.method == "POST":
            so_phong = request.form.get("so_phong", "").strip()
            if not so_phong:
                raise BillingError("Chưa nhập số phòng")
            values = (
                so_phong, _int("tang", 1), float(request.form.get("dien_tich") or 0),
                _int("gia_thang"), _int("gia_ngay"), _int("so_nguoi_toi_da", 2),
                request.form.get("ghi_chu", "").strip(),
            )
            try:
                if phong is None:
                    conn.execute(
                        "INSERT INTO phong (so_phong, tang, dien_tich, gia_thang, gia_ngay, "
                        "so_nguoi_toi_da, ghi_chu) VALUES (?, ?, ?, ?, ?, ?, ?)", values)
                else:
                    conn.execute(
                        "UPDATE phong SET so_phong=?, tang=?, dien_tich=?, gia_thang=?, gia_ngay=?, "
                        "so_nguoi_toi_da=?, ghi_chu=? WHERE id=?", values + (pid,))
                conn.commit()
            except db.sqlite3.IntegrityError:
                raise BillingError(f"Số phòng '{so_phong}' đã tồn tại")
            flash("Đã lưu phòng", "ok")
            return redirect(url_for("phong_list"))
        return render_template("phong_form.html", phong=phong)

    @app.route("/phong/<int:pid>")
    def phong_detail(pid):
        conn = get_db()
        phong = conn.execute("SELECT * FROM phong WHERE id = ?", (pid,)).fetchone() or abort(404)
        nguoi = conn.execute(
            "SELECT * FROM nguoi_thue WHERE phong_id = ? ORDER BY ngay_ra IS NOT NULL, ngay_vao DESC",
            (pid,)).fetchall()
        chi_so = conn.execute(
            "SELECT * FROM chi_so WHERE phong_id = ? ORDER BY ngay_ghi DESC LIMIT 24", (pid,)).fetchall()
        hoa_don = conn.execute(
            "SELECT * FROM hoa_don WHERE phong_id = ? ORDER BY tu_ngay DESC", (pid,)).fetchall()
        return render_template("phong_detail.html", phong=phong, nguoi=nguoi,
                               chi_so=chi_so, hoa_don=hoa_don, today=date.today().isoformat())

    # ---------- Người thuê ----------
    @app.route("/nguoi-thue")
    def nguoi_list():
        tat_ca = request.args.get("tat_ca") == "1"
        sql = ("SELECT n.*, p.so_phong FROM nguoi_thue n JOIN phong p ON p.id = n.phong_id "
               + ("" if tat_ca else "WHERE n.ngay_ra IS NULL ") + "ORDER BY p.so_phong, n.ho_ten")
        return render_template("nguoi_list.html", nguoi=get_db().execute(sql).fetchall(), tat_ca=tat_ca)

    @app.route("/nguoi-thue/them", methods=["GET", "POST"])
    @app.route("/nguoi-thue/<int:nid>/sua", methods=["GET", "POST"])
    def nguoi_form(nid=None):
        conn = get_db()
        nguoi = None
        if nid is not None:
            nguoi = conn.execute("SELECT * FROM nguoi_thue WHERE id = ?", (nid,)).fetchone() or abort(404)
        if request.method == "POST":
            ho_ten = request.form.get("ho_ten", "").strip()
            if not ho_ten:
                raise BillingError("Chưa nhập họ tên")
            phong_id = _int("phong_id")
            if not conn.execute("SELECT 1 FROM phong WHERE id = ?", (phong_id,)).fetchone():
                raise BillingError("Chưa chọn phòng")
            ngay_ra = request.form.get("ngay_ra", "").strip() or None
            values = (
                phong_id, ho_ten, *(request.form.get(k, "").strip()
                                    for k in ("cccd", "sdt", "ngay_sinh", "que_quan")),
                _date("ngay_vao").isoformat(), ngay_ra, request.form.get("ghi_chu", "").strip(),
            )
            if nguoi is None:
                conn.execute(
                    "INSERT INTO nguoi_thue (phong_id, ho_ten, cccd, sdt, ngay_sinh, que_quan, "
                    "ngay_vao, ngay_ra, ghi_chu) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
            else:
                conn.execute(
                    "UPDATE nguoi_thue SET phong_id=?, ho_ten=?, cccd=?, sdt=?, ngay_sinh=?, "
                    "que_quan=?, ngay_vao=?, ngay_ra=?, ghi_chu=? WHERE id=?", values + (nid,))
            conn.commit()
            flash("Đã lưu người thuê", "ok")
            return redirect(url_for("phong_detail", pid=phong_id))
        return render_template("nguoi_form.html", nguoi=nguoi, phongs=db.danh_sach_phong(conn),
                               phong_id=request.args.get("phong_id", type=int),
                               today=date.today().isoformat())

    @app.post("/nguoi-thue/<int:nid>/tra-phong")
    def nguoi_tra_phong(nid):
        conn = get_db()
        n = conn.execute("SELECT * FROM nguoi_thue WHERE id = ?", (nid,)).fetchone() or abort(404)
        conn.execute("UPDATE nguoi_thue SET ngay_ra = ? WHERE id = ?", (_date("ngay_ra").isoformat(), nid))
        conn.commit()
        flash(f"{n['ho_ten']} đã trả phòng", "ok")
        return redirect(url_for("phong_detail", pid=n["phong_id"]))

    # ---------- Chỉ số điện nước ----------
    @app.route("/chi-so", methods=["GET", "POST"])
    def chi_so():
        conn = get_db()
        if request.method == "POST":
            phong_id = _int("phong_id")
            ngay = _date("ngay_ghi").isoformat()
            dien, nuoc = _int("dien"), _int("nuoc")
            truoc = conn.execute(
                "SELECT * FROM chi_so WHERE phong_id = ? AND ngay_ghi < ? ORDER BY ngay_ghi DESC LIMIT 1",
                (phong_id, ngay)).fetchone()
            if truoc and (dien < truoc["dien"] or nuoc < truoc["nuoc"]):
                raise BillingError(
                    f"Chỉ số nhỏ hơn lần ghi trước ({truoc['ngay_ghi']}: điện {truoc['dien']}, nước {truoc['nuoc']})")
            conn.execute(
                "INSERT INTO chi_so (phong_id, ngay_ghi, dien, nuoc) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(phong_id, ngay_ghi) DO UPDATE SET dien = excluded.dien, nuoc = excluded.nuoc",
                (phong_id, ngay, dien, nuoc))
            conn.commit()
            flash("Đã ghi chỉ số", "ok")
            return redirect(request.form.get("next") or url_for("chi_so"))
        rows = conn.execute(
            "SELECT c.*, p.so_phong FROM chi_so c JOIN phong p ON p.id = c.phong_id "
            "ORDER BY c.ngay_ghi DESC, p.so_phong LIMIT 200").fetchall()
        return render_template("chi_so.html", rows=rows, phongs=db.danh_sach_phong(conn),
                               today=date.today().isoformat())

    # ---------- Hóa đơn ----------
    @app.route("/hoa-don")
    def hoa_don_list():
        thang = request.args.get("thang", "")
        trang_thai = request.args.get("trang_thai", "")
        sql = "SELECT h.*, p.so_phong FROM hoa_don h JOIN phong p ON p.id = h.phong_id WHERE 1=1"
        args = []
        if thang:
            sql += " AND substr(h.den_ngay, 1, 7) = ?"
            args.append(thang)
        if trang_thai in ("0", "1"):
            sql += " AND h.da_thanh_toan = ?"
            args.append(int(trang_thai))
        rows = get_db().execute(sql + " ORDER BY h.den_ngay DESC, p.so_phong", args).fetchall()
        tong = sum(r["tong"] for r in rows)
        return render_template("hoa_don_list.html", rows=rows, thang=thang,
                               trang_thai=trang_thai, tong=tong)

    @app.route("/hoa-don/tao", methods=["GET", "POST"])
    def hoa_don_tao():
        conn = get_db()
        if request.method == "POST":
            phong_id = _int("phong_id")
            phong = conn.execute("SELECT * FROM phong WHERE id = ?", (phong_id,)).fetchone()
            if not phong:
                raise BillingError("Chưa chọn phòng")
            loai = request.form.get("loai", "thang")
            tu, den = _date("tu_ngay"), _date("den_ngay")
            gia_dien, gia_nuoc = db.get_cau_hinh(conn, "don_gia_dien"), db.get_cau_hinh(conn, "don_gia_nuoc")
            d = dict(dien_cu=_int("dien_cu"), dien_moi=_int("dien_moi"),
                     nuoc_cu=_int("nuoc_cu"), nuoc_moi=_int("nuoc_moi"))
            kq = tinh_hoa_don(loai, phong["gia_thang"], phong["gia_ngay"], tu, den,
                              d["dien_cu"], d["dien_moi"], d["nuoc_cu"], d["nuoc_moi"],
                              gia_dien, gia_nuoc, _int("phi_khac"))
            cur = conn.execute(
                """INSERT INTO hoa_don (phong_id, loai, tu_ngay, den_ngay, so_ngay, dien_cu, dien_moi,
                   nuoc_cu, nuoc_moi, don_gia_dien, don_gia_nuoc, tien_phong, tien_dien, tien_nuoc,
                   phi_khac, tong, ghi_chu) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (phong_id, loai, tu.isoformat(), den.isoformat(), kq.so_ngay, d["dien_cu"], d["dien_moi"],
                 d["nuoc_cu"], d["nuoc_moi"], gia_dien, gia_nuoc, kq.tien_phong, kq.tien_dien,
                 kq.tien_nuoc, kq.phi_khac, kq.tong, request.form.get("ghi_chu", "").strip()))
            conn.commit()
            flash("Đã tạo hóa đơn", "ok")
            return redirect(url_for("hoa_don_xem", hid=cur.lastrowid))

        # GET: điền sẵn kỳ và chỉ số từ dữ liệu đã ghi
        today = date.today()
        phong_id = request.args.get("phong_id", type=int)
        loai = request.args.get("loai", "thang")
        tu = request.args.get("tu_ngay") or today.replace(day=1).isoformat()
        den = request.args.get("den_ngay") or today.replace(
            day=calendar.monthrange(today.year, today.month)[1]).isoformat()
        goi_y = {"dien_cu": "", "dien_moi": "", "nuoc_cu": "", "nuoc_moi": ""}
        if phong_id:
            cu = db.chi_so_truoc(conn, phong_id, tu)
            moi = db.chi_so_truoc(conn, phong_id, den)
            if cu:
                goi_y["dien_cu"], goi_y["nuoc_cu"] = cu["dien"], cu["nuoc"]
            if moi:
                goi_y["dien_moi"], goi_y["nuoc_moi"] = moi["dien"], moi["nuoc"]
        return render_template("hoa_don_tao.html", phongs=db.danh_sach_phong(conn), phong_id=phong_id,
                               loai=loai, tu=tu, den=den, goi_y=goi_y,
                               gia_dien=db.get_cau_hinh(conn, "don_gia_dien"),
                               gia_nuoc=db.get_cau_hinh(conn, "don_gia_nuoc"))

    @app.route("/hoa-don/<int:hid>")
    def hoa_don_xem(hid):
        h = get_db().execute(
            "SELECT h.*, p.so_phong FROM hoa_don h JOIN phong p ON p.id = h.phong_id WHERE h.id = ?",
            (hid,)).fetchone() or abort(404)
        return render_template("hoa_don_xem.html", h=h, today=date.today().isoformat())

    @app.post("/hoa-don/<int:hid>/thanh-toan")
    def hoa_don_thanh_toan(hid):
        conn = get_db()
        if request.form.get("huy") == "1":
            conn.execute("UPDATE hoa_don SET da_thanh_toan = 0, ngay_thanh_toan = NULL WHERE id = ?", (hid,))
        else:
            conn.execute("UPDATE hoa_don SET da_thanh_toan = 1, ngay_thanh_toan = ? WHERE id = ?",
                         (_date("ngay_thanh_toan").isoformat(), hid))
        conn.commit()
        return redirect(url_for("hoa_don_xem", hid=hid))

    @app.post("/hoa-don/<int:hid>/xoa")
    def hoa_don_xoa(hid):
        conn = get_db()
        conn.execute("DELETE FROM hoa_don WHERE id = ?", (hid,))
        conn.commit()
        flash("Đã xóa hóa đơn", "ok")
        return redirect(url_for("hoa_don_list"))

    # ---------- Cấu hình ----------
    @app.route("/cau-hinh", methods=["GET", "POST"])
    def cau_hinh():
        conn = get_db()
        if request.method == "POST":
            for k in ("don_gia_dien", "don_gia_nuoc"):
                v = _int(k)
                if v < 0:
                    raise BillingError("Đơn giá không được âm")
                db.set_cau_hinh(conn, k, v)
            flash("Đã lưu đơn giá", "ok")
            return redirect(url_for("cau_hinh"))
        return render_template("cau_hinh.html", gia_dien=db.get_cau_hinh(conn, "don_gia_dien"),
                               gia_nuoc=db.get_cau_hinh(conn, "don_gia_nuoc"))

    return app
