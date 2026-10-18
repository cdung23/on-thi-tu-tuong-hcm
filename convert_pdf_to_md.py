import os
import sys
import io
import time
import json
import base64
import requests
import pypdfium2 as pdfium

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
MODEL_NAME = "gemini-3.1-flash-lite"
PDF_PATH = r"e:\Học phần\HK1_2026-2027\Tư tưởng HCM\Trắc nghiệm.pdf"
OUTPUT_MD = r"e:\Học phần\HK1_2026-2027\Tư tưởng HCM\Trắc nghiệm.md"
CHECKPOINT_PATH = r"e:\Học phần\HK1_2026-2027\Tư tưởng HCM\.ocr_checkpoint.json"

URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

PROMPT = """Trích xuất toàn bộ câu hỏi trắc nghiệm tiếng Việt trong ảnh dưới dạng JSON.
Định dạng JSON:
{
  "tieu_de": "Tên chương hoặc phần nếu có, không có thì null",
  "danh_sach_cau": [
    {
      "cau_so": "Số thứ tự câu (vd: 4, 5, hoặc chuỗi), không rõ thì ghi thứ tự",
      "cau_hoi": "Nội dung câu hỏi đầy đủ...",
      "lua_chon": [
        {"nhan": "A", "noi_dung": "..."},
        {"nhan": "B", "noi_dung": "..."},
        {"nhan": "C", "noi_dung": "..."},
        {"nhan": "D", "noi_dung": "..."}
      ],
      "dap_an_danh_dau": "A/B/C/D nếu trong ảnh có khoanh tròn hoặc gạch chân đáp án đúng, không có thì null",
      "chu_thich": "Chú thích footnote nếu có, không có thì null"
    }
  ]
}
Yêu cầu bắt buộc:
- Nhận diện 100% tiếng Việt có dấu chuẩn xác tuyệt đối, không bỏ sót từ hay dấu câu.
- Bỏ qua các hình mờ nền, vết nhòe mực, dòng chữ quảng cáo scan ("Được quét bằng CamScanner") và các ghi chú viết tay rác không thuộc nội dung đề thi."""

def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_checkpoint(data):
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_page_to_markdown(data):
    md_lines = []
    tieu_de = data.get("tieu_de")
    def safe_str(val):
        if val is None:
            return ""
        return str(val).strip()

    tieu_de = safe_str(data.get("tieu_de"))
    if tieu_de:
        md_lines.append(f"\n## {tieu_de}\n")
    
    cau_list = data.get("danh_sach_cau", [])
    if not isinstance(cau_list, list):
        cau_list = []

    for item in cau_list:
        if not isinstance(item, dict):
            continue
        cau_so = safe_str(item.get("cau_so"))
        cau_hoi = safe_str(item.get("cau_hoi"))
        lua_chon = item.get("lua_chon", [])
        dap_an = safe_str(item.get("dap_an_danh_dau")).upper()
        chu_thich = safe_str(item.get("chu_thich"))

        if cau_so:
            md_lines.append(f"### Câu {cau_so}")
        else:
            md_lines.append("### Câu hỏi")
        
        if cau_hoi:
            md_lines.append(f"{cau_hoi}\n")

        if isinstance(lua_chon, list):
            for opt in lua_chon:
                if isinstance(opt, dict):
                    nhan = safe_str(opt.get("nhan")).upper()
                    noi_dung = safe_str(opt.get("noi_dung"))
                else:
                    nhan = ""
                    noi_dung = safe_str(opt)
                
                if dap_an and nhan and nhan == dap_an:
                    md_lines.append(f"- **{nhan}. {noi_dung}** *(Đáp án đánh dấu)*")
                elif nhan:
                    md_lines.append(f"- {nhan}. {noi_dung}")
                elif noi_dung:
                    md_lines.append(f"- {noi_dung}")
        
        if chu_thich:
            md_lines.append(f"\n> *Chú thích: {chu_thich}*")
        
        md_lines.append("") # Dòng trống giữa các câu
    
    return "\n".join(md_lines)

def process_page(doc, page_idx):
    page = doc[page_idx]
    pil_img = page.render(scale=1.5).to_pil()
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=85)
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    payload = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]
        }],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    max_retries = 6
    backoff = 4
    for attempt in range(max_retries):
        try:
            resp = requests.post(URL, json=payload, timeout=75)
            if resp.status_code == 200:
                resp_json = resp.json()
                candidate = resp_json.get('candidates', [{}])[0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    raw_text = candidate['content']['parts'][0]['text']
                    return json.loads(raw_text)
                else:
                    finish_reason = candidate.get('finishReason', 'UNKNOWN')
                    print(f"Trang {page_idx + 1}: finishReason = {finish_reason}")
                    return {"tieu_de": None, "danh_sach_cau": []}
            elif resp.status_code == 429:
                print(f"Trang {page_idx + 1}: Chạm rate limit (429). Đang chờ {backoff * 2}s...")
                time.sleep(backoff * 2)
                backoff *= 1.5
            else:
                print(f"Trang {page_idx + 1}: Lỗi HTTP {resp.status_code}. Thử lại lần {attempt + 1}...")
                time.sleep(backoff)
                backoff *= 1.5
        except Exception as e:
            print(f"Trang {page_idx + 1}: Lỗi kết nối ({e}). Đang thử lại lần {attempt + 1}...")
            time.sleep(backoff)
            backoff *= 1.5

    raise RuntimeError(f"Không thể xử lý trang {page_idx + 1} sau {max_retries} lần thử.")

def main():
    print(f"Bắt đầu chuyển đổi: {PDF_PATH}")
    doc = pdfium.PdfDocument(PDF_PATH)
    total_pages = len(doc)
    print(f"Tổng số trang: {total_pages}")

    checkpoint = load_checkpoint()
    
    # Khởi tạo tệp Markdown nếu chưa có
    if not os.path.exists(OUTPUT_MD) or len(checkpoint) == 0:
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write("# TÀI LIỆU ÔN TẬP TRẮC NGHIỆM TƯ TƯỞNG HỒ CHÍ MINH\n\n")
            f.write("> Tài liệu được chuyển đổi và số hóa tự động với độ chính xác cao từ bản PDF scan.\n\n---\n")

    start_time = time.time()
    last_title = ""

    for i in range(total_pages):
        page_key = str(i + 1)
        if page_key in checkpoint:
            print(f"[{i + 1}/{total_pages}] Đã có trong checkpoint. Bỏ qua.")
            continue

        print(f"[{i + 1}/{total_pages}] Đang nhận diện trang {i + 1}...")
        t0 = time.time()
        page_data = process_page(doc, i)
        t_page = time.time() - t0

        num_questions = len(page_data.get("danh_sach_cau", []))
        print(f"[{i + 1}/{total_pages}] Xong ({t_page:.1f}s) - Phát hiện {num_questions} câu trắc nghiệm.")

        # Lọc tiêu đề trùng lặp nếu trang kế tiếp lặp lại tên chương
        current_title = page_data.get("tieu_de")
        if current_title and current_title == last_title:
            page_data["tieu_de"] = None
        elif current_title:
            last_title = current_title

        md_content = format_page_to_markdown(page_data)
        if md_content.strip():
            with open(OUTPUT_MD, "a", encoding="utf-8") as f:
                f.write(f"\n<!-- Trang {i + 1} -->\n")
                f.write(md_content)
                f.write("\n")

        checkpoint[page_key] = {
            "num_questions": num_questions,
            "status": "success",
            "title": current_title
        }
        save_checkpoint(checkpoint)

        # Điều tiết nhịp gọi API để duy trì dưới 15 RPM
        time.sleep(4.2)

    total_time = (time.time() - start_time) / 60
    total_q = sum(v.get("num_questions", 0) for v in checkpoint.values() if isinstance(v, dict))
    print(f"\nHOÀN THÀNH TOÀN BỘ 116 TRANG TRONG {total_time:.1f} PHÚT!")
    print(f"Tổng số câu trắc nghiệm đã trích xuất: {total_q}")
    print(f"Tệp kết quả: {OUTPUT_MD}")

if __name__ == "__main__":
    main()
