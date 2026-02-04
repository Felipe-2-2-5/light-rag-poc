<a id='1e1dc384-82f6-489c-8325-728ac1d7e31f'></a>

Final Project

<a id='6db45486-c4fd-4a42-99ed-b2aeb436ad92'></a>

FINAL PROJECT

<a id='40f2593d-4c72-443f-bc97-4062a301dbec'></a>

1. Thông tin chung

<table><thead><tr><th></th><th></th></tr></thead><tbody><tr><td>Môn học</td><td>NLP501 - Natural Language Processing</td></tr><tr><td>Trọng số</td><td>50% tổng điểm</td></tr><tr><td>Hình thức</td><td>Cá nhân hoặc Nhóm (1-3 members)</td></tr><tr><td>Thời gian</td><td>Trước buổi 10</td></tr><tr><td>Ngôn ngữ</td><td>Python (TensorFlow/PyTorch)</td></tr></tbody></table>

<a id='ca02c380-a90b-41cb-815f-4c3b88c331fd'></a>

2. Timeline
<table id="0-1">
<tr><td id="0-2">Mốc</td><td id="0-3">Thời gian</td><td id="0-4">Hoạt động</td></tr>
<tr><td id="0-5">Nộp bài</td><td id="0-6">Trước buổi 10 (1-3 ngày)</td><td id="0-7">Submit code + báo cáo</td></tr>
<tr><td id="0-8">Trình bày</td><td id="0-9">Buổi 10</td><td id="0-a">Present và demo dự án</td></tr>
</table>

<a id='dbd273b0-6a86-4401-ad62-90026e1bcd08'></a>

3. Các lựa chọn đề tài
Sinh viên tham khảo trong đề tài sau hoặc tự đề xuất đề tài phù hợp với nội dung
môn học:

<a id='a115abd9-c688-42cb-88a3-d185dd32ce3e'></a>

Option A: End-to-End Chatbot
Xây dựng chatbot cho một domain cụ thể với khả năng hội thoại nhiều lượt.

<a id='3e6b7675-5ee1-4c4d-9397-64786a7000d7'></a>

Mô tả
Phát triển một chatbot có khả năng hiểu và trả lời câu hỏi trong một lĩnh vực cụ thể (customer service, FAQ bot, booking assistant, etc.). Chatbot phải xử lý được multi-turn conversations và duy trì context.

<a id='b6c929aa-4d91-468f-8e69-fa1bebd9c7f5'></a>

Yêu cầu:
1. Triển khai Seq2Seq architecture với Attention mechanism
2. Xử lý multi-turn dialogue với conversation history
3. Intent classification để hiểu ý định người dùng
4. Entity extraction để trích xuất thông tin quan trọng
5. Response generation với beam search hoặc sampling
6. Simple UI/Interface cho demo (Gradio, Streamlit, hoặc CLI)

<a id='24c0e907-2520-4a24-b06f-4a20020767d7'></a>

Dataset gợi ý
* Cornell Movie Dialogs Corpus
* DailyDialog Dataset
* MultiWOZ (task-oriented dialogues)
* Tự tạo dataset cho domain cụ thể

<a id='8ef57dce-0ec0-42f9-ac7b-2344c6e762e5'></a>

## Evaluation Metrics
* BLEU score cho response quality

<a id='e97aad88-4e4d-4729-b633-69a42224fab5'></a>

Page 1 of 5

<!-- PAGE BREAK -->

<a id='fc78f774-d713-41ca-b23a-95a1b8718c7a'></a>

Final Project

<a id='e3018afe-296a-438f-9816-d2868dbb75cd'></a>

- Human evaluation (coherence, relevance, fluency)
- Intent accuracy (nếu có intent classification)
- Task completion rate (cho task-oriented chatbot)

<a id='73f48e19-6807-414d-ae9d-5764e1976263'></a>

Option B: Machine Translation System
Xây dựng hệ thống dịch máy neural cho một cặp ngôn ngữ.

<a id='91bf4a4f-e915-4ae5-9778-e7c3524c30ae'></a>

Mô tả
Phát triển Neural Machine Translation (NMT) system để dịch giữa hai ngôn ngữ (khuyến khích
Vietnamese-English hoặc English-Vietnamese). Hệ thống phải sử dụng encoder-decoder
architecture với attention.

<a id='f993b9e4-ddf2-4f98-9334-5968312acf07'></a>

Yêu cầu:
1. Encoder-Decoder architecture với LSTM/GRU hoặc Transformer
2. Attention mechanism (Bahdanau hoặc Luong attention)
3. Subword tokenization (BPE hoặc SentencePiece)
4. Beam search decoding với adjustable beam width
5. Handling of unknown words (UNK tokens)
6. Interactive translation interface

<a id='8dd95c4a-d482-4bfc-babf-5bf7376c6076'></a>

Dataset gợi ý
* IWSLT (TED Talks translation)
* WMT datasets
* Tatoeba (sentence pairs)
* PhoMT (Vietnamese-English parallel corpus)
* OpenSubtitles

<a id='13d21f81-eafd-4ffb-b8a1-789def2c4605'></a>

## Evaluation Metrics
* BLEU score (corpus-level và sentence-level)
* METEOR score
* Human evaluation (adequacy, fluency)
* Attention visualization

<a id='e5d6a693-2e6b-4cc9-b48d-3367fdec4aef'></a>

Option C: Text Summarization System
Xây dựng hệ thống tóm tắt văn bản tự động.

<a id='5bf6b6fc-c889-4a63-9348-82b92d9dff08'></a>

Mô tả
Phát triển hệ thống có khả năng tóm tắt văn bản dài thành bản tóm tắt ngắn gọn. Có thể chọn extractive summarization (chọn câu quan trọng) hoặc abstractive summarization (sinh câu mới).

<a id='f7420605-3787-406c-b2ef-3b1a2a69ea91'></a>

Yêu cầu:
1. Chọn một approach: Extractive HOẶC Abstractive (hoặc cả hai)

<a id='8820e3d0-dfbc-4111-9e92-063daf25a05b'></a>

Page 2 of 5

<!-- PAGE BREAK -->

<a id='98afabea-4a1a-45af-85d8-33484240e562'></a>

Final Project

<a id='eece2c2e-f50a-462a-b497-d54f60590f60'></a>

2. Extractive: sentence scoring, sentence selection, redundancy removal
3. Abstractive: Seq2Seq với attention, copy mechanism (optional)
4. Xử lý văn bản dài (truncation, chunking strategies)
5. Length control cho output summary
6. Web interface để demo với input documents

<a id='f96774b3-683e-4d98-bebc-6d2030d8fec1'></a>

Dataset gợi ý

* CNN/DailyMail Dataset
* XSum (BBC articles)
* Multi-News (multi-document summarization)
* Vietnamese news dataset (tự thu thập)
* arXiv/PubMed (scientific papers)

<a id='61ed09a4-62a1-4cce-bd4b-fd4b6a0dbc6a'></a>

Evaluation Metrics

* ROUGE scores (ROUGE-1, ROUGE-2, ROUGE-L)
* BLEU score
* Human evaluation (informativeness, coherence, conciseness)
* Compression ratio

<a id='0eb7dccb-68b9-4b6c-afad-acce32301cb2'></a>

Option D: Question Answering System

<a id='5111111a-ec7c-41d3-92a5-affa7319f2e5'></a>

Xây dựng hệ thống trả lời câu hỏi dựa trên văn bản.

<a id='103978cc-5588-42c3-826d-537e1d5411bd'></a>

Mô tả
Phát triển hệ thống QA có khả năng trả lời câu hỏi dựa trên một corpus văn bản cho trước.
Hệ thống bao gồm document retrieval và answer extraction/generation.

<a id='97063445-ff0a-43bf-9af3-d6aa8b7f81e3'></a>

Yêu cầu:
1. Document Retriever: TF-IDF, BM25, hoặc dense retrieval
2. Reader/Extractor: span extraction hoặc answer generation
3. Xử lý multiple documents (ranking, re-ranking)
4. Handling no-answer cases
5. Confidence scoring cho answers
6. Simple Q&A interface cho demo

<a id='711de3b8-4675-40bb-9fe4-e50d469ff722'></a>

Dataset gợi ý

* SQuAD 2.0 (Stanford Question Answering Dataset)
* Natural Questions (Google)
* TriviaQA
* HotpotQA (multi-hop reasoning)
* Vietnamese QA dataset (UIT-ViQuAD)

<a id='69f7af98-5371-4e80-94ef-f0be7a57ca45'></a>

Evaluation Metrics
* Exact Match (EM)

<a id='64d14129-4286-4038-90c4-cab24919a244'></a>

Page 3 of 5

<!-- PAGE BREAK -->

<a id='1b98cb2f-f328-4290-a960-d1de2451b7ce'></a>

Final Project

<a id='fa6e6a67-0095-4913-8413-34b46beb1576'></a>

* F1 score (token-level overlap)
* Mean Reciprocal Rank (MRR) cho retrieval
* Human evaluation (correctness, completeness)

<a id='210c407d-4be9-4a83-a0f2-84da6a7231c4'></a>

## 4. Sản phẩm nộp
Tất cả các sản phẩm cần được nộp trước buổi 10 (1-3 ngày):

<a id='710dd042-5c84-43a1-80b7-4a96e228a1ef'></a>

## 4.1. Source Code
1. GitHub repository (public hoặc private với access cho giảng viên)
2. Cấu trúc thư mục rõ ràng: /src, /data, /models, /notebooks, /docs
3. Requirements.txt hoặc environment.yml
4. README.md với hướng dẫn cài đặt và chạy
5. Training scripts và inference scripts tách biệt

<a id='b1d4b43a-08e5-4c33-a735-c60bc88df8be'></a>

## 4.2. Trained Models

* Model weights (upload Google Drive/Hugging Face nếu file lớn)
* Model configuration files
* Tokenizer/Vocabulary files

<a id='212d883e-4243-481f-b7e1-a8c91662e582'></a>

## 4.3. Report (8-10 trang)

* Abstract: Tóm tắt project
* Introduction: Mô tả bài toán và motivation
* Related Work: Tổng quan các phương pháp liên quan
* Methodology: Chi tiết architecture và approach
* Experiments: Dataset, training setup, hyperparameters
* Results: Kết quả với tables và figures
* Analysis: Phân tích lỗi, case studies
* Conclusion: Kết luận và future work

<a id='834d2398-a6c0-42d2-bdc9-d51b488303ec'></a>

## 4.4. Presentation Slides

*   10-12 slides cho phần trình bày (10 phút)
*   Bao gồm demo live

<a id='b367d4a0-219e-4553-8ed4-644958d080fc'></a>

5. Tiêu chí đánh giá
<table id="3-1">
<tr><td id="3-2">Tiêu chí</td><td id="3-3">Tỷ trọng</td><td id="3-4">Điểm</td><td id="3-5">Mô tả</td></tr>
<tr><td id="3-6">Accuracy &amp; Correctness</td><td id="3-7">25%</td><td id="3-8">2.5</td><td id="3-9">Mô hình hoạt động đúng, kết quả chính xác</td></tr>
<tr><td id="3-a">Creativity &amp; Problem-Solving</td><td id="3-b">20%</td><td id="3-c">2.0</td><td id="3-d">Có sáng tạo, giải quyết vấn đề hiệu quả</td></tr>
<tr><td id="3-e">Completeness (Code + Docs)</td><td id="3-f">20%</td><td id="3-g">2.0</td><td id="3-h">Code đầy đủ, documentation chi tiết</td></tr>
<tr><td id="3-i">Presentation Skills</td><td id="3-j">15%</td><td id="3-k">1.5</td><td id="3-l">Trình bày rõ ràng, demo mượt mà</td></tr>
<tr><td id="3-m">Theoretical Application</td><td id="3-n">15%</td><td id="3-o">1.5</td><td id="3-p">Áp dụng kiến thức lý thuyết đúng đắn</td></tr>
<tr><td id="3-q">Timeliness &amp; Requirements</td><td id="3-r">5%</td><td id="3-s">0.5</td><td id="3-t">Nộp đúng hạn, đúng yêu cầu</td></tr>
</table>

<a id='06bb2449-7f8e-404c-9db2-3f24cd3f3df8'></a>

Page 4 of 5

<!-- PAGE BREAK -->

<a id='167b042e-3de7-481b-b015-f0cce253120f'></a>

Final Project

<a id='9cc52b1c-a8dd-4d90-93c1-b78cf6a6a59a'></a>

<table id="4-1">
<tr><td id="4-2">Tiêu chí</td><td id="4-3">Tỷ trọng</td><td id="4-4">Điểm</td><td id="4-5">Mô tả</td></tr>
<tr><td id="4-6">TỔNG CÔNG</td><td id="4-7">100%</td><td id="4-8">10.0</td><td id="4-9">Quy về 50% tổng điểm môn học</td></tr>
</table>

<a id='082eccd3-42bd-4bb3-9622-f0f232ebf6f5'></a>

Page 5 of 5