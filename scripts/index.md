# scripts 目次

- `scripts/gpt5_hallucinations.csv` — 検証用データセット（質問/回答/正解）。
- `scripts/suppression_prompt.txt` — 抑制プロンプト雛形（必要に応じて原典の本文に差し替え可）。
- `scripts/eval_hallucination_prompt.py` — Responses APIを用いた検証スクリプト。

実行例:

```bash
uv add openai pandas python-dotenv
uv run python scripts/eval_hallucination_prompt.py \
  --input scripts/gpt5_hallucinations.csv \
  --model gpt-5 \
  --prompt-file scripts/suppression_prompt.txt
```

出力:

- `eval_results.csv` — 質問, 回答(観測), 正解, プロンプトなし出力, プロンプトあり出力
- `logs/eval_*.jsonl` — 実行ログ(JSONL, コンソールにも同時出力)

