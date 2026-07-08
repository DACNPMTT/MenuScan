# OCR Baseline Report

## Dataset
- **Version**: menuscan-ocr-benchmark.v1
- **Samples**: 22 Vietnamese-source menus
- **Generator**: `doc/ocr-benchmark/generate_fixtures.ps1`
- **Coverage**: Single/multi-column, multi-page, skewed, low quality, price formats, bilingual gloss, etc.

## Parser Accuracy Baseline (Mock Perfect OCR)
Đánh giá chất lượng của `RuleBasedMenuParser` khi nhận được kết quả OCR hoàn hảo (text ground truth):

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Price Accuracy | ≥ 0.95 | > 0.95 | ✅ Pass |
| Name Accuracy (overall) | ≥ 0.85 | > 0.85 | ✅ Pass |
| Name Acc (Single Column) | ≥ 0.90 | > 0.90 | ✅ Pass |
| Name Acc (Multi Column) | ≥ 0.75 | ~ 0.79 | ✅ Pass |

## OCR Provider Baseline: Google Vision API
Đánh giá chất lượng end-to-end với dữ liệu thật, chạy qua `GoogleVisionOcrProvider` (mô hình `DOCUMENT_TEXT_DETECTION`).

| Metric | MVP Gate | Actual | Status |
|--------|----------|--------|--------|
| CER (Character Error Rate)| ≤ 0.08 | 0.146 | ❌ Fail |
| WER (Word Error Rate) | ≤ 0.18 | 0.269 | ❌ Fail |
| Price Accuracy | ≥ 0.95 | 0.318 | ❌ Fail |
| Line Recall | ≥ 0.90 | 0.369 | ❌ Fail |
| Processing Time (Mean) | - | 625 ms | ✅ Fast |
| Processing Time (p95) | ≤ 5000ms | 1344 ms | ✅ Pass |

## Known Limitations (Lỗi tồn tại)

1. **Google Vision Text Extraction Performance**:
   Chỉ số CER và WER hiện tại (0.146 và 0.269) vượt quá ngưỡng chấp nhận của MVP (0.08 và 0.18). Khả năng nhận diện giá (Price Accuracy) và recall dòng chữ (Line Recall) rất thấp.
   - Nguyên nhân chính: Google Vision thường không gom nhóm tốt chữ trên cùng một dòng ngang trong các layout menu nhiều cột hoặc xa nhau (bảng giá).
   - Adapter hiện tại chưa thực hiện thuật toán gióng dòng (horizontal alignment) lại từ block bounding boxes.

2. **Column Count Detection**:
   Hiện tại `GoogleVisionOcrProvider` chưa trả về được `column_index` cho từng block, dẫn đến Column Accuracy = 0.

3. **Variant Menus**:
   `RuleBasedMenuParser` và `menu_table.build_menu_table` hiện đã hỗ trợ một số layout biến thể phổ biến: header món nền + các dòng biến thể có giá, có `base_name`, `variant_name`, và `variant_group="size"` khi nhận diện kích cỡ. Giới hạn còn lại nằm ở chất lượng OCR/line grouping của provider trên ảnh thật.
