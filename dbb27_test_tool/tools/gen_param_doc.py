"""Sinh tài liệu Word mô tả thông số, từ viết tắt và giới hạn của máy DBB-27.

Chạy:  .venv\\Scripts\\python.exe tools\\gen_param_doc.py
Kết quả: docs\\DBB-27_Thong_so_va_gioi_han.docx
"""
import os
from datetime import date

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "DBB-27_Thong_so_va_gioi_han.docx")

HEADER_BG = "1F4E79"   # xanh đậm
ZEBRA_BG = "EAF1F8"    # xanh nhạt

# --- Từ viết tắt ---
ABBREV = [
    ("UF", "Ultrafiltration", "Siêu lọc (rút dịch khỏi máu)"),
    ("UF goal", "Ultrafiltration goal", "Lượng dịch cần rút (đặt trước)"),
    ("UF volume", "Ultrafiltration volume", "Lượng dịch đã rút thực tế"),
    ("UF rate", "Ultrafiltration rate", "Tốc độ rút dịch"),
    ("TMP", "Trans-Membrane Pressure", "Áp lực xuyên màng lọc"),
    ("HD", "Hemodialysis", "Lọc máu (thẩm tách) thông thường"),
    ("ECUM", "Extracorporeal Ultrafiltration Method", "Chế độ siêu lọc đơn thuần (rút dịch, không thẩm tách)"),
    ("BP", "Blood Pressure", "Huyết áp"),
    ("Venous pressure", "Venous pressure", "Áp lực đường máu về (tĩnh mạch)"),
    ("Dialysate", "Dialysate", "Dịch lọc (dịch thẩm tách)"),
    ("Conductivity", "Conductivity", "Độ dẫn điện của dịch lọc (phản ánh nồng độ điện giải)"),
    ("Heparin", "Heparin", "Thuốc chống đông (bơm bằng infusion pump)"),
    ("CP", "Central management computer", "Máy tính quản lý trung tâm (PC bác sĩ)"),
    ("RS-232C", "Recommended Standard 232", "Chuẩn truyền nối tiếp"),
    ("TCP/IP", "Transmission Control Protocol / Internet Protocol", "Giao thức mạng (cổng RJ45)"),
    ("ASCII", "American Standard Code for Information Interchange", "Bảng mã ký tự dùng cho dữ liệu"),
    ("STX", "Start of Text", "Mã bắt đầu khung (ở đây là 'K' '2')"),
    ("ETX", "End of Text", "Mã kết thúc khung (CR, LF)"),
    ("LEN", "Length", "Số byte của vùng dữ liệu RES-DATA (3 chữ số)"),
    ("SUM", "Checksum", "Mã kiểm tra tổng (2 ký tự hex)"),
    ("CR / LF", "Carriage Return / Line Feed", "Ký tự xuống dòng (0x0D, 0x0A)"),
    ("mmHg", "millimeter of mercury", "Đơn vị áp suất"),
    ("mS/cm", "milliSiemens per centimeter", "Đơn vị độ dẫn điện"),
    ("bpm", "beats per minute", "Nhịp/phút (mạch)"),
    ("mL/min, mL/hr", "milliliter per minute / hour", "Đơn vị lưu lượng"),
    ("L, L/hr", "liter / liter per hour", "Đơn vị thể tích / lưu lượng"),
]

# No, Tên VI, Tên EN, ID, Đơn vị, Kích thước, Kiểu, Giới hạn/khoảng tham khảo, Ghi chú
PARAMS = [
    (1, "Mục tiêu siêu lọc", "UF goal", "A", "L", "5 byte", "Số thập phân", "0 – 5 L (thường 1 – 4 L)", "Giá trị đặt"),
    (2, "Thể tích đã siêu lọc", "UF volume", "B", "L", "5 byte", "Số thập phân", "0 – (UF goal)", "Giá trị thực"),
    (3, "Tốc độ siêu lọc", "UF rate", "C", "L/hr", "5 byte", "Số thập phân", "0 – 2.0 L/hr (an toàn thường < 1.0 – 1.5)", "Giá trị thực"),
    (4, "Tốc độ bơm máu", "Blood pump flow rate", "D", "mL/min", "5 byte", "Số thập phân", "0 – 500 mL/min (thường 200 – 400)", "Giá trị thực"),
    (5, "Tốc độ bơm Heparin", "Infusion (Heparin) pump rate", "E", "mL/hr", "5 byte", "Số thập phân", "0 – 10 mL/hr (thường 1 – 3)", "Giá trị đặt"),
    (6, "Nhiệt độ dịch lọc", "Dialysate temperature", "F", "°C", "5 byte", "Số thập phân", "35 – 39 °C (thường 36 – 37)", "Giá trị thực"),
    (7, "Độ dẫn điện dịch lọc", "Dialysate conductivity", "G", "mS/cm", "5 byte", "Số thập phân", "12.5 – 15.5 mS/cm (thường 13.5 – 14.5)", "Giá trị thực"),
    (8, "Áp lực tĩnh mạch", "Venous pressure", "H", "mmHg", "5 byte", "Số thập phân", "khoảng +50 – +250 mmHg", "Giá trị thực; có thể âm"),
    (9, "Áp lực dịch lọc", "Dialysate pressure", "I", "mmHg", "5 byte", "Số thập phân", "khoảng -200 – +50 mmHg", "Giá trị thực; thường âm"),
    (10, "Áp lực xuyên màng (TMP)", "TMP", "J", "mmHg", "5 byte", "Số thập phân", "0 – 300 mmHg (cảnh báo khi cao)", "Giá trị thực"),
    (11, "Thời gian điều trị", "Treatment time", "K", "min", "5 byte", "Số thập phân", "0 – 479 phút", "Theo tài liệu: < 479 min"),
    (12, "Lưu lượng dịch lọc", "Dialysate flow rate", "L", "mL/min", "5 byte", "Số thập phân", "300 – 800 mL/min (thường 500)", ""),
    (13, "CB Nhiệt độ dịch", "Dialysate temperature alarm", "a", "—", "1 byte", "Cờ 0/1", "0 = bình thường, 1 = cảnh báo", ""),
    (14, "CB Độ dẫn điện", "Conductivity alarm", "b", "—", "1 byte", "Cờ 0/1", "0 = bình thường, 1 = cảnh báo", ""),
    (15, "CB Áp lực tĩnh mạch", "Venous pressure alarm", "c", "—", "1 byte", "Cờ 0/1", "0 = bình thường, 1 = cảnh báo", ""),
    (16, "CB Áp lực dịch lọc", "Dialysate pressure alarm", "d", "—", "1 byte", "Cờ 0/1", "0 = bình thường, 1 = cảnh báo", ""),
    (17, "CB TMP", "TMP alarm", "e", "—", "1 byte", "Cờ 0/1", "0 = bình thường, 1 = cảnh báo", ""),
    (18, "CB Khí (bọt khí)", "Air alarm", "f", "—", "1 byte", "Cờ 0/1", "0 = bình thường, 1 = cảnh báo", "An toàn quan trọng"),
    (19, "CB Rò máu", "Blood leak alarm", "g", "—", "1 byte", "Cờ 0/1", "0 = bình thường, 1 = cảnh báo", "An toàn quan trọng"),
    (20, "CB Khác", "Other alarm", "h", "—", "1 byte", "Cờ 0/1", "0 = bình thường, 1 = cảnh báo", "Mọi cảnh báo ngoài 13–19 và 31"),
    (21, "Cờ đang điều trị", "Under treatment flag", "M", "—", "1 byte", "Cờ 0/1", "1 = đang điều trị, 0 = không", "Connection/Treatment/Disconnect"),
    (22, "Chế độ điều trị", "Treatment mode", "N", "—", "1 byte", "Cờ 0/1", "0 = HD, 1 = ECUM", ""),
    (23, "Mục tiêu bù dịch", "Substitution goal", "O", "L", "5 byte", "Không dùng", "Luôn = 0", "Máy không hỗ trợ"),
    (24, "Thể tích bù dịch", "Substitution volume", "P", "L", "5 byte", "Không dùng", "Luôn = 0", "Máy không hỗ trợ"),
    (25, "Tốc độ bù dịch", "Substitution rate", "Q", "L/hr", "5 byte", "Không dùng", "Luôn = 0", "Máy không hỗ trợ"),
    (26, "Nhiệt độ bù dịch", "Substitution temperature", "R", "°C", "5 byte", "Không dùng", "Luôn = 0", "Máy không hỗ trợ"),
    (27, "Giờ đo huyết áp", "BP measurement time", "S", "HHMMSS", "5 byte", "Thời gian", "24 giờ (HHMMSS)", "Lần đo gần nhất"),
    (28, "Huyết áp tâm thu", "Systolic blood pressure", "T", "mmHg", "5 byte", "Số thập phân", "60 – 250 mmHg", "Lần đo gần nhất"),
    (29, "Huyết áp tâm trương", "Diastolic blood pressure", "U", "mmHg", "5 byte", "Số thập phân", "40 – 150 mmHg", "Lần đo gần nhất"),
    (30, "Mạch", "Pulse", "V", "bpm", "5 byte", "Số thập phân", "30 – 200 bpm", "Lần đo gần nhất"),
    (31, "CB Huyết áp", "Blood pressure alarm", "i", "—", "1 byte", "Cờ 0/1", "0 = bình thường, 1 = cảnh báo", ""),
]


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:fill"), color)
    tcPr.append(sh)


def set_cell(cell, text, *, bold=False, white=False, size=9, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    if align:
        p.alignment = align
    run = p.add_run(str(text))
    run.bold = bold
    run.font.size = Pt(size)
    if white:
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def add_table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = "Table Grid"
    for i, h in enumerate(headers):
        set_cell(t.rows[0].cells[i], h, bold=True, white=True, size=9,
                 align=WD_ALIGN_PARAGRAPH.CENTER)
        shade(t.rows[0].cells[i], HEADER_BG)
    for r, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            set_cell(cells[i], val, size=9)
            if r % 2 == 1:
                shade(cells[i], ZEBRA_BG)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = w
    return t


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)

    title = doc.add_heading("Máy lọc thận Nikkiso DBB-27", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph("Tài liệu mô tả thông số, từ viết tắt và giới hạn (tham khảo)")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.runs[0].italic = True
    meta = doc.add_paragraph(f"Phiên bản: {date.today():%d/%m/%Y}  ·  Nguồn: Nikkiso Communication Protocol for DBB-27")
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.runs[0].font.size = Pt(9)

    # Cảnh báo y tế
    warn = doc.add_paragraph()
    rw = warn.add_run("⚠ LƯU Ý: Các giá trị giới hạn trong tài liệu là KHOẢNG THAM KHẢO lâm sàng/kỹ thuật, "
                      "KHÔNG phải ngưỡng cảnh báo chính thức của máy. Ngưỡng cảnh báo thực tế do máy DBB-27 và "
                      "nhân viên y tế cài đặt; phải đối chiếu với cấu hình máy trước khi sử dụng cho lâm sàng.")
    rw.bold = True
    rw.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    rw.font.size = Pt(9)

    # 1. Tổng quan giao tiếp
    doc.add_heading("1. Tổng quan giao tiếp", level=1)
    doc.add_paragraph(
        "Máy tính (CP) gửi lệnh, máy DBB-27 trả về dữ liệu. Lệnh hỏi gồm 3 byte: ký tự \"K\", CR, LF. "
        "Máy trả về một khung có dạng:")
    p = doc.add_paragraph()
    p.add_run("STX (\"K\",\"2\")  +  LEN (3 byte)  +  RES-DATA  +  SUM (2 byte)  +  ETX (CR, LF)").bold = True
    add_table(doc,
        ["Thông số", "Giá trị"],
        [
            ["Chuẩn truyền", "RS-232C (cổng DSUB) hoặc TCP/IP (cổng RJ45)"],
            ["Tốc độ", "9.600 bps"],
            ["Khung dữ liệu", "8 bit dữ liệu, 1 stop bit, không parity"],
            ["Điều khiển luồng", "Không (Xon/Xoff: none)"],
            ["Bảng mã", "ASCII"],
            ["Cáp", "RS-232 9 chân, đấu chéo (cross / null-modem)"],
        ])

    # 2. Từ viết tắt
    doc.add_heading("2. Bảng từ viết tắt", level=1)
    add_table(doc, ["Viết tắt", "Tiếng Anh đầy đủ", "Giải thích"],
              [[a, b, c] for a, b, c in ABBREV])

    # 3. Bảng thông số
    doc.add_heading("3. Bảng 31 thông số truyền về", level=1)
    doc.add_paragraph("ID là mã định danh 1 ký tự đứng trước giá trị trong khung RES-DATA.").runs[0].font.size = Pt(9)
    add_table(doc,
        ["No.", "Tên (Tiếng Việt)", "Tên (English)", "ID", "Đơn vị", "Kích thước", "Kiểu", "Giới hạn / khoảng tham khảo", "Ghi chú"],
        PARAMS)

    # 4. Quy ước định dạng
    doc.add_heading("4. Quy ước định dạng dữ liệu", level=1)
    for line in [
        "Mục 1–12: số 5 chữ số có dấu thập phân; nếu âm thì ký tự đầu là \"-\". "
        "Ví dụ UF goal 2.35 L → \"0\",\"2\",\".\",\"3\",\"5\"; áp lực -146 mmHg → \"-\",\"0\",\"1\",\"4\",\"6\".",
        "Cảnh báo (mục 13–20, 31): \"1\" = có cảnh báo, \"0\" = bình thường.",
        "Mục 20 (Cảnh báo khác) gộp mọi cảnh báo ngoài mục 13–19 và 31.",
        "Cờ đang điều trị (mục 21): \"1\" khi đang ở chế độ Connection/Treatment/Disconnect.",
        "Chế độ điều trị (mục 22): HD = \"0\", ECUM = \"1\".",
        "Mục 23–26 (bù dịch): máy không hỗ trợ, luôn trả về 0.",
        "Giờ đo huyết áp (mục 27): định dạng 24 giờ; mục 27–30 là kết quả đo gần nhất.",
        "SUM (checksum): cộng giá trị các byte (trừ CR, LF), lấy 2 chữ số hex cuối, mã hóa ASCII.",
    ]:
        doc.add_paragraph(line, style="List Bullet").runs[0].font.size = Pt(9.5)

    doc.add_paragraph()
    note = doc.add_paragraph()
    note.add_run("Ghi chú kỹ thuật: ").bold = True
    note.add_run("Một số chi tiết trong tài liệu gốc cần xác minh với máy thật — cách tính checksum, "
                 "định dạng \"Thời gian điều trị\" và \"Giờ đo huyết áp\". Công cụ DBB-27 Serial Test Tool "
                 "hiển thị khung thô (raw) cùng checksum nhận/tính để đối chiếu.").font.size = Pt(9)

    doc.save(OUT)
    print("Saved:", OUT)


if __name__ == "__main__":
    main()
