**hallucination-test**

- Repository: https://github.com/noricha-vr/hallucination-test
- 目的: TechnoEdge が紹介した OpenAI+Georgia Tech の新論文「Why Language Models Hallucinate」の示す「確信度しきい値＋減点容認」指示（例: 75%以上の確信があるときのみ回答。正答+1/誤答-2/無回答0）によるハルシネーション抑制効果を、実装直結で検証する最小セット。

**できること**
- 検証CSV（質問/回答/正解）を使い、同一質問を2条件で実行
  - ベースライン（プロンプトなし）
  - 抑制プロンプトあり（75%しきい値＋減点容認の方針）
- OpenAI Responses API（推奨）で呼び出し、`eval_results.csv`に比較出力
- gpt‑5の実行要件（`input_text`形式、`reasoning.effort=minimal` など）に合わせた安定化済み
- ログはJSONLで`logs/`に保存（print未使用、構造化ログ）

**ディレクトリ**
- `scripts/gpt5_hallucinations.csv` … 観測例CSV（1–4: GPT‑5観測、5–6: 他モデル観測）
- `scripts/suppression_prompt.txt` … 抑制プロンプト雛形（原典本文に差し替え可）
- `scripts/eval_hallucination_prompt.py` … 検証スクリプト（Responses API/Chat対応、JSONログ）
- `logs/` … 実行ログ（JSONL）
- `eval_results.csv` … 実行結果（生成物。git管理外）

**セットアップ**
- 前提: Python 3.13, uv, OpenAI API Key
  - `brew install uv`（未導入の場合）
  - `export OPENAI_API_KEY=sk-...`（環境変数に設定）
- 依存インストール（uvロックに基づく）
  - `uv sync`

**基本の実行**
- gpt‑5（推奨のResponses APIで実行）
  - `uv run python scripts/eval_hallucination_prompt.py --input scripts/gpt5_hallucinations.csv --model gpt-5 --prompt-file scripts/suppression_prompt.txt`
- 参考: 安定比較用に gpt‑4o‑mini でも再現可
  - `uv run python scripts/eval_hallucination_prompt.py --input scripts/gpt5_hallucinations.csv --model gpt-4o-mini --prompt-file scripts/suppression_prompt.txt`

注意（gpt‑5のAPI仕様メモ）
- Responses API: `content`は`{"type":"input_text","text":"..."}`を使用
- `reasoning.effort`を`minimal`に指定すると`output_text`が安定
- `max_output_tokens`は16以上。`temperature`は未指定（モデル仕様）
- Chat Completionsにフォールバックする際は`max_completion_tokens`を使用（`max_tokens`は非対応）

**検証タスク（CSVの中身）**
- 文字カウント（例: “Northern Territory” の 'r' / “blueberry” の 'b'）
- 厳密綴り出力（例: “Northern Territory”）
- 列挙（例: 名前に'r'を含む米国の州一覧）
- 事実知識（例: Adam Tauman Kalai 博士論文タイトル）

**gpt‑5 検証結果（2025‑09‑09, `scripts/suppression_prompt.txt`使用）**
- Q1 文字カウント（'r' in “Northern Territory”）
  - なし: 3（誤） / あり: 2（誤）
- Q2 文字カウント（'b' in “blueberry”）
  - なし: 2（正） / あり: 2（正）
- Q3 列挙（'r'を含む米州名のアルファベット順列挙）
  - なし: 過剰列挙・混入で不正確 / あり: 「わからない」を選択（誤答回避）
- Q4 厳密綴り（“Northern Territory”）
  - なし: 正 / あり: 正
- Q5 文字カウント（'D' in “DEEPSEEK”）
  - なし: 正 / あり: 正
- Q6 事実知識（Kalai 博士論文タイトル）
  - なし: 誤答 / あり: 「わからない」（誤答回避）

所感（例の採点: 正答+1 / 誤答-2 / 無回答0）
- ベースライン: 正3・誤3 → 合計 -3
- 抑制あり: 正3・誤1・無回答2 → 合計 +1
- 誤答の大幅減（特に知識系: Q3, Q6）。一方、単純カウント系（Q1）は未改善で、抑制プロンプトに「数えに確信が持てない場合は無回答」と明記すると更に抑制が効く余地あり。

**出力ファイル**
- `eval_results.csv` … 「質問, 回答(観測), 正解, プロンプトなし出力, プロンプトあり出力」
- `logs/eval_*.jsonl` … 実行ログ（JSONL, コンソールにも同時出力）

**プロンプト差し替え**
- 既定は雛形です。原典（TechnoEdge 記事/論文）の抑制プロンプト本文を`scripts/suppression_prompt.txt`に貼り付け直して再実行してください。

**参考リンク**
- TechnoEdge: https://www.techno-edge.net/article/2025/09/08/4574.html
- OpenAI 公式ブログ: https://openai.com/index/why-language-models-hallucinate/
- GPT‑5 開発者向け: https://openai.com/index/introducing-gpt-5-for-developers/
- The Guardian（GPT‑5の誤答事例）: https://www.theguardian.com/australia-news/2025/aug/08/openai-chatgpt-5-struggled-with-spelling-and-geography
- Kieran Healy（blueberry事例）: https://kieranhealy.org/blog/archives/2025/08/07/blueberry-hill/
- HNまとめ: https://news.ycombinator.com/item?id=44832908
- Kalai 博士論文（正解ソース）: https://csd.cmu.edu/sites/default/files/phd-thesis/CMU-CS-01-132.pdf

**開発メモ**
- uv/pyprojectで依存管理。実行は`uv run`を推奨
- ログは`logger`（JSON）に集約。printは使用しない
- 生成物/ログは`.gitignore`で除外

ライセンス: 本検証で使用する記事/論文の引用は各原典のライセンス・利用規約に従ってください
