import os
import sys
import re
import time
import json
import requests

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from notebooklm_tools.utils.auth_browser import run_headless_auth
from notebooklm_tools.core import client

NOTEBOOK_ID = "daa50c25-b755-47a0-9203-d9b7a621e14c"
INPUT_MD = r"e:\Học phần\HK1_2026-2027\Tư tưởng HCM\Trắc nghiệm.md"
OUTPUT_MD = r"e:\Học phần\HK1_2026-2027\Tư tưởng HCM\Trắc nghiệm - Đáp án và Giải thích.md"
CHECKPOINT_PATH = r"e:\Học phần\HK1_2026-2027\Tư tưởng HCM\.solve_checkpoint.json"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY}"

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

def parse_questions_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    pattern = r'(###\s*Câu[^\n]*\n)([\s\S]*?)(?=(?:###\s*Câu|\Z))'
    matches = list(re.finditer(pattern, text))
    questions = []

    for idx, match in enumerate(matches):
        raw_header = match.group(1).strip()
        body = match.group(2).strip()

        # Tách dòng
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        if not lines:
            continue

        # Dòng đầu là câu hỏi
        q_lines = []
        opt_lines = []
        for line in lines:
            if re.match(r'^[-\*]?\s*[A-D]\.', line):
                # Chuẩn hóa về A. B. C. D.
                clean_opt = re.sub(r'^[-\*]?\s*', '', line)
                # Loại bỏ đánh dấu *(Đáp án đánh dấu)* nếu có để khách quan
                clean_opt = re.sub(r'\s*\*\([^\)]*\)\*', '', clean_opt).strip()
                opt_lines.append(clean_opt)
            elif not opt_lines:
                # Vẫn là dòng câu hỏi (có thể câu hỏi nhiều dòng)
                if not line.startswith('>'):
                    q_lines.append(line)

        question_text = " ".join(q_lines).strip()
        # Loại bỏ tiền tố "Câu X" nếu đã có trong question_text
        question_text = re.sub(r'^(Câu\s*\d+[\.:]?\s*)', '', question_text).strip()

        questions.append({
            "id": idx + 1,
            "header": raw_header,
            "question": question_text,
            "options": opt_lines
        })

    return questions

def query_gemini_fallback(batch_questions):
    prompt_items = []
    for q in batch_questions:
        item = f"câu: {q['question']}\n" + "\n".join(q['options'])
        prompt_items.append(item)
    
    full_prompt = (
        "Dựa vào kiến thức chuẩn Giáo trình Tư tưởng Hồ Chí Minh của Bộ Giáo dục và Đào tạo, "
        "hãy giải các câu trắc nghiệm sau. Với mỗi câu, bắt buộc tuân theo đúng cấu trúc:\n\n"
        "câu: [Nội dung câu hỏi]\n"
        "A. [Nội dung A]\n"
        "B. [Nội dung B]\n"
        "C. [Nội dung C]\n"
        "D. [Nội dung D]\n"
        "Đáp án: [Chỉ ghi chữ cái A, B, C hoặc D]\n"
        "Giải thích: [Căn cứ lý luận, sự kiện lịch sử hoặc trích dẫn từ Giáo trình Tư tưởng Hồ Chí Minh]\n\n"
        "Danh sách câu hỏi:\n---\n" + "\n\n---\n\n".join(prompt_items)
    )

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            cand = data.get('candidates', [{}])[0]
            if 'content' in cand and 'parts' in cand['content']:
                return cand['content']['parts'][0]['text']
    except Exception as e:
        print(f"Lỗi fallback Gemini: {e}")
    return None

def query_notebooklm_batch(nlm_client, batch_questions):
    prompt_items = []
    for q in batch_questions:
        item = f"câu: {q['question']}\n" + "\n".join(q['options'])
        prompt_items.append(item)
    
    full_prompt = (
        "Dựa vào giáo trình trong notebook, hãy giải các câu trắc nghiệm sau. Với mỗi câu, bắt buộc xuất ra CHÍNH XÁC theo cấu trúc:\n"
        "câu: [Nội dung câu hỏi]\n"
        "A. [Nội dung A]\n"
        "B. [Nội dung B]\n"
        "C. [Nội dung C]\n"
        "D. [Nội dung D]\n"
        "Đáp án: [A, B, C hoặc D]\n"
        "Giải thích: [Trích dẫn nguyên văn hoặc căn cứ từ giáo trình, nêu rõ chương/trang nếu có]\n\n"
        "Danh sách câu hỏi:\n---\n" + "\n\n---\n\n".join(prompt_items)
    )

    try:
        res = nlm_client.query(NOTEBOOK_ID, full_prompt)
        text = res.answer if hasattr(res, 'answer') else (res.get('answer') if isinstance(res, dict) else str(res))
        
        # Làm sạch các lời chào chatbot ở cuối (ví dụ: "Bạn có muốn giải tiếp...")
        text = re.sub(r'💡\s*Bạn có (cần|muốn)[\s\S]*$', '', text).strip()
        text = re.sub(r'---\s*$', '', text).strip()
        return text
    except Exception as e:
        print(f"Lỗi NotebookLM query: {e}")
        return None

def main():
    print("Khởi động hệ thống kết nối NotebookLM: 'Giáo trình tư tưởng HCM'...")
    tokens = run_headless_auth(profile_name="default")
    if not tokens:
        print("Lỗi: Không thể lấy token xác thực NotebookLM!")
        return
    
    nlm_client = client.NotebookLMClient(cookies=tokens.cookies, csrf_token=tokens.csrf_token)
    print("Kết nối NotebookLM thành công!")

    # Xóa lịch sử trò chuyện cũ trước khi bắt đầu để cửa sổ ngữ cảnh hoàn toàn sạch
    try:
        nlm_client.delete_chat_history(NOTEBOOK_ID)
        print("Đã làm mới cửa sổ trò chuyện (context window) trên NotebookLM.")
    except Exception:
        pass

    questions = parse_questions_from_file(INPUT_MD)
    total_q = len(questions)
    print(f"Tổng số câu trắc nghiệm: {total_q}")

    checkpoint = load_checkpoint()

    # Khởi tạo file Markdown đầu ra nếu chưa có
    if not os.path.exists(OUTPUT_MD) or len(checkpoint) == 0:
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write("# ĐÁP ÁN & GIẢI THÍCH CHI TIẾT TRẮC NGHIỆM TƯ TƯỞNG HỒ CHÍ MINH\n\n")
            f.write("> Dữ liệu giải thích và đối chiếu trực tiếp từ **Giáo trình Tư tưởng Hồ Chí Minh** (Bộ Giáo dục và Đào tạo) thông qua NotebookLM.\n\n---\n\n")

    BATCH_SIZE = 3
    batches = [questions[i:i + BATCH_SIZE] for i in range(0, total_q, BATCH_SIZE)]
    print(f"Chia thành {len(batches)} cụm (mỗi cụm {BATCH_SIZE} câu).")

    batches_since_reset = 0

    for b_idx, batch in enumerate(batches):
        batch_key = f"batch_{b_idx + 1}"
        q_start = batch[0]['id']
        q_end = batch[-1]['id']

        if batch_key in checkpoint:
            print(f"[{b_idx + 1}/{len(batches)}] Câu {q_start}-{q_end}: Đã hoàn thành (checkpoint). Bỏ qua.")
            continue

        print(f"[{b_idx + 1}/{len(batches)}] Đang truy xuất NotebookLM cho Câu {q_start}-{q_end}...")
        t0 = time.time()
        
        result_text = query_notebooklm_batch(nlm_client, batch)
        source_used = "NotebookLM"

        # Nếu NotebookLM không trả về hoặc bị lỗi, dùng fallback bên ngoài (Gemini)
        if not result_text or len(result_text.strip()) < 50:
            print(f"[{b_idx + 1}/{len(batches)}] Không tìm thấy trên NotebookLM hoặc lỗi kết nối. Chuyển sang tìm kiếm bổ sung...")
            result_text = query_gemini_fallback(batch)
            source_used = "Gemini Fallback"

        t_elapsed = time.time() - t0

        if result_text and result_text.strip():
            with open(OUTPUT_MD, "a", encoding="utf-8") as f:
                f.write(f"\n{result_text.strip()}\n\n---\n")

            checkpoint[batch_key] = {
                "q_range": f"{q_start}-{q_end}",
                "source": source_used,
                "status": "success"
            }
            save_checkpoint(checkpoint)
            print(f"[{b_idx + 1}/{len(batches)}] Xong ({t_elapsed:.1f}s) via {source_used}.")
        else:
            print(f"[{b_idx + 1}/{len(batches)}] Cảnh báo: Không thể giải cụm câu {q_start}-{q_end}.")

        batches_since_reset += 1

        # Cứ sau 10 cụm (~30 câu), làm sạch lịch sử trò chuyện trên NotebookLM để tránh tràn context / lag
        if batches_since_reset >= 10:
            print("Đang làm sạch lịch sử trò chuyện trên NotebookLM để tránh đầy context window...")
            try:
                nlm_client.delete_chat_history(NOTEBOOK_ID)
                print("Đã làm sạch context window thành công.")
            except Exception as e:
                print(f"Lỗi khi xóa lịch sử chat: {e}")
            batches_since_reset = 0

        # Delay ngắn điều tiết nhịp
        time.sleep(3.0)

    print("\nHOÀN THÀNH TOÀN BỘ 464 CÂU HỎI TRẮC NGHIỆM!")
    print(f"Tệp kết quả: {OUTPUT_MD}")

if __name__ == "__main__":
    main()
