# hallucination-test

最初に「何をしたか（やったこと）」と「結果（結論）」を示します。

## 実施内容と結論（最初に読む）
- やったこと
  - TechnoEdge が紹介した OpenAI + Georgia Tech の新論文に基づき、「確信度しきい値（≥75%）＋減点容認（正答+1/誤答-2/無回答0）」の抑制プロンプトが本当に効くかを、A/B（プロンプトなし vs あり）で検証しました。
  - データセット（観測例）をCSV化し、OpenAI Responses API を使う検証スクリプトで同一設問を2条件実行。モデルは gpt‑5（必要に応じて gpt‑4o‑mini でも再現可）。
  - gpt‑5 の仕様に合わせ、`input_text` 形式＋ `reasoning.effort=minimal` ＋ `max_output_tokens>=16` で安定取得するよう実装。
- 結果（gpt‑5, 2025‑09‑09）
  - 知識系（列挙/固有名）では「誤答→わからない」へ切り替わり、減点を回避（例: 米州リスト、Kalai 論文タイトル）。
  - 単純カウント（“Northern Territory” の 'r'）は未改善。
  - 簡易スコア: ベースライン -3 → 抑制あり +1（正3/誤1/無回答2）。
- 最短再現
  ```bash
  export OPENAI_API_KEY=sk-...
  uv sync
  uv run python scripts/eval_hallucination_prompt.py \
    --input scripts/gpt5_hallucinations.csv \
    --model gpt-5 \
    --prompt-file scripts/suppression_prompt.txt
  ```

- リポジトリ: https://github.com/noricha-vr/hallucination-test

---

## TL;DR（やれること）
- 同一の設問を「プロンプトなし」と「抑制プロンプトあり」で実行し、出力を比較。
- gpt‑5 の Responses API 仕様（`input_text`、`reasoning.effort=minimal`、`max_output_tokens>=16`）に対応済み。
- 結果は `eval_results.csv`、ログは `logs/*.jsonl` に保存。

## できること
- A/B 実行: ベースライン（プロンプトなし） vs 抑制プロンプトあり
- Responses API を利用した安定実行（gpt‑5対応）
- 結果 CSV 出力（質問, 観測回答, 正解, なし出力, あり出力）
- 構造化ログ（JSONL）

## ディレクトリ構成
- `scripts/gpt5_hallucinations.csv` — 観測例データ（1–4: GPT‑5、5–6: 他モデル）
- `scripts/suppression_prompt.txt` — 抑制プロンプト雛形（原典本文に差し替え可）
- `scripts/eval_hallucination_prompt.py` — 検証スクリプト（Responses/Chat両対応、JSONログ）
- `logs/` — 実行ログ（JSONL）
- `eval_results.csv` — 実行結果（生成物。git 管理外）

## セットアップ
前提: Python 3.13、uv、OpenAI API Key

1) uv を用意（未導入なら）
```bash
brew install uv
```

2) 環境変数を設定
```bash
export OPENAI_API_KEY=sk-xxxxxxxx
```

3) 依存を同期
```bash
uv sync
```

## 実行方法
gpt‑5（Responses API）で検証する場合:
```bash
uv run python scripts/eval_hallucination_prompt.py \
  --input scripts/gpt5_hallucinations.csv \
  --model gpt-5 \
  --prompt-file scripts/suppression_prompt.txt
```

参考: 比較用に gpt‑4o‑mini でも実行可
```bash
uv run python scripts/eval_hallucination_prompt.py \
  --input scripts/gpt5_hallucinations.csv \
  --model gpt-4o-mini \
  --prompt-file scripts/suppression_prompt.txt
```

### gpt‑5 モデル注意点（Responses API）
- `content` は `{"type":"input_text","text":"..."}` を使用
- `reasoning.effort` は `minimal` が推奨（`output_text` 安定化）
- `max_output_tokens` は 16 以上を指定
- `temperature` は未指定（モデル側の既定に従う）
- Chat Completions へフォールバックする場合は `max_completion_tokens` を使用（`max_tokens` 非対応）

## データセット（設問の型）
- 文字カウント: “Northern Territory” の 'r'、 “blueberry” の 'b'
- 厳密綴り: “Northern Territory” を完全一致で出力
- 列挙: 名前に 'r' を含む米国の州名（アルファベット順、カンマ区切り）
- 事実知識: Adam Tauman Kalai 博士論文タイトル

## 検証結果サマリ（gpt‑5, 2025‑09‑09）
`scripts/suppression_prompt.txt` の雛形を使用した実行結果の要約です。

| ID | タスク | なし | あり | 所見 |
|---:|---|---|---|---|
| 1 | 'r' in “Northern Territory” | 3（誤） | 2（誤） | 未改善 |
| 2 | 'b' in “blueberry” | 2（正） | 2（正） | 問題なし |
| 3 | 'r'含む米州の列挙 | 過剰・混入で不正確 | わからない | 誤答回避 |
| 4 | “Northern Territory” 厳密綴り | 正 | 正 | 安定 |
| 5 | 'D' in “DEEPSEEK” | 正 | 正 | 安定 |
| 6 | Kalai 博士論文タイトル | 誤答 | わからない | 誤答回避 |

簡易スコア（正答+1 / 誤答-2 / 無回答0）:
- ベースライン: 正3・誤3 → 合計 -3
- 抑制あり: 正3・誤1・無回答2 → 合計 +1

知識系（列挙・固有名）は誤答から「無回答」へシフトし、減点リスクを回避。一方で単純カウント（Q1）は改善せず。
必要に応じて抑制プロンプトに「カウントへ確信が持てない場合は無回答」を明記すると、更なる抑制が期待できます。

## 出力物
- `eval_results.csv` — 列: `質問, 回答(観測), 正解, プロンプトなし出力, プロンプトあり出力`
- `logs/eval_*.jsonl` — 構造化ログ（JSONL）

## プロンプト差し替え
`scripts/suppression_prompt.txt` は雛形です。TechnoEdge 記事や論文の抑制プロンプト本文をそのまま貼り替えて再実行してください。

## 再現手順（フル）
1) このリポジトリをクローン
```bash
git clone https://github.com/noricha-vr/hallucination-test
cd hallucination-test
```
2) API Key と依存を用意
```bash
export OPENAI_API_KEY=sk-...
uv sync
```
3) 実行
```bash
uv run python scripts/eval_hallucination_prompt.py \
  --input scripts/gpt5_hallucinations.csv \
  --model gpt-5 \
  --prompt-file scripts/suppression_prompt.txt
```
4) 結果確認
```bash
sed -n '1,80p' eval_results.csv
```

## 参考
- TechnoEdge: https://www.techno-edge.net/article/2025/09/08/4574.html
- OpenAI 公式ブログ: https://openai.com/index/why-language-models-hallucinate/
- GPT‑5 開発者向け: https://openai.com/index/introducing-gpt-5-for-developers/
- The Guardian（GPT‑5の誤答事例）: https://www.theguardian.com/australia-news/2025/aug/08/openai-chatgpt-5-struggled-with-spelling-and-geography
- Kieran Healy（blueberry 事例）: https://kieranhealy.org/blog/archives/2025/08/07/blueberry-hill/
- HN まとめ: https://news.ycombinator.com/item?id=44832908
- Kalai 博士論文（正解ソース）: https://csd.cmu.edu/sites/default/files/phd-thesis/CMU-CS-01-132.pdf

## メモ
- 依存は uv / pyproject で管理。実行は `uv run` 推奨
- ログは `logger`（JSON）に集約。print は使用しません
- 生成物・ログは `.gitignore` で除外しています
