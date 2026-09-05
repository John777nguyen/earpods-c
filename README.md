# TGDD EarPods Watcher

Tool tự động quét trang **Máy đổi trả – Tai nghe Apple** trên
thegioididong.com:

https://www.thegioididong.com/may-doi-tra/tai-nghe-apple

Khi phát hiện có sản phẩm **EarPods** xuất hiện (còn để bán, không bị đánh
dấu hết hàng) mà lần quét trước chưa có, tool sẽ gửi tin nhắn Telegram báo
ngay. Chạy hoàn toàn miễn phí trên **GitHub Actions** — vừa chạy theo lịch
(cron, mặc định 15 phút/lần) vừa có thể bấm nút chạy thủ công bất cứ lúc
nào.

## 1. Tạo Telegram Bot + lấy Chat ID

1. Mở Telegram, chat với **@BotFather** → gõ `/newbot` → đặt tên → nó trả
   về cho bạn một **token** dạng `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxx`.
   Đây là `TG_BOT_TOKEN`.
2. Nhắn thử 1 tin bất kỳ cho bot vừa tạo (bắt buộc, để bot "biết" chat với
   bạn).
3. Mở trình duyệt, truy cập:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   (thay `<TOKEN>` bằng token ở bước 1). Tìm số ở mục `"chat":{"id": ...}` —
   đó là `TG_CHAT_ID` của bạn.

## 2. Đưa code này lên GitHub

1. Tạo một repo mới trên GitHub (có thể để **Private**).
2. Đẩy toàn bộ thư mục này lên repo đó, ví dụ:
   ```bash
   git init
   git add .
   git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/<user>/<repo>.git
   git push -u origin main
   ```

## 3. Thêm Secrets cho repo

Vào repo trên GitHub → **Settings → Secrets and variables → Actions →
New repository secret**, tạo 2 secrets:

| Name | Value |
|---|---|
| `TG_BOT_TOKEN` | token bot ở bước 1 |
| `TG_CHAT_ID` | chat id ở bước 1 |

## 4. Chạy thử thủ công

Vào tab **Actions** trên GitHub → chọn workflow **"Check EarPods on TGDD
trade-in page"** → bấm **Run workflow** (nút màu xanh) để chạy ngay, không
cần chờ tới lịch cron. Sau khi chạy xong, xem log để biết tool có tìm thấy
EarPods hay không.

Sau đó tool sẽ tự chạy lại mỗi 15 phút theo lịch cron trong
`.github/workflows/check-earpods.yml` (GitHub Actions đôi khi trễ vài phút
vào giờ cao điểm, đây là giới hạn chung của GitHub, không phải lỗi code).

## 5. Cách hoạt động / lưu ý

- Kết quả quét được so sánh với `state.json` (được tool tự commit lại vào
  repo sau mỗi lần chạy) để chỉ báo khi có sản phẩm **mới** xuất hiện,
  tránh việc bị nhắn tin lặp lại liên tục.
- Trang TGDD có thể thay đổi cấu trúc HTML theo thời gian. Nếu sau này
  tool không còn phát hiện đúng (báo thiếu hoặc không báo), mở
  `scraper.py`, xem hàm `find_earpods_items()` — trước tiên hàm cố parse
  theo cấu trúc `ul.listproduct li.item` (cấu trúc phổ biến hiện tại của
  TGDD); nếu không khớp, tự động chuyển sang cách quét toàn bộ thẻ `<a>`
  chứa chữ "EarPods" trong trang (ít chính xác hơn nhưng khó bị "gãy" khi
  đổi giao diện).
- Nếu muốn quét nhanh/chậm hơn 15 phút, sửa dòng `cron: "*/15 * * * *"`
  trong file workflow (định dạng cron chuẩn, phút giờ ngày tháng thứ).
- Tool chỉ đọc trang công khai bằng `requests`, không đăng nhập, không
  submit form gì cả.

## Cấu trúc project

```
.
├── scraper.py                        # logic quét + gửi Telegram
├── state.json                        # trạng thái đã thông báo (tool tự cập nhật)
├── requirements.txt                  # thư viện Python cần cài
└── .github/workflows/check-earpods.yml   # lịch chạy trên GitHub Actions
```
