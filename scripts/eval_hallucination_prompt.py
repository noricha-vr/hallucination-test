#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ハルシネーション抑制プロンプトの有効性検証スクリプト。

入力CSV（質問/回答/正解）を読み込み、同一質問に対して
 (A) ベースライン（プロンプトなし）
 (B) 抑制プロンプトあり（system相当）
の2通りでOpenAI Responses APIを呼び、結果をeval_results.csvに保存する。

依存: openai, pandas, python-dotenv
実行例:
  uv run python scripts/eval_hallucination_prompt.py \
    --input scripts/gpt5_hallucinations.csv \
    --prompt-file scripts/suppression_prompt.txt \
    --model gpt-5
"""

import argparse
import datetime as dt
import json
import os
import sys
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
from openai import OpenAI


# 簡易JSONロガー（print禁止のため）
class JsonLogger:
    def __init__(self, logfile: str):
        self.logfile = logfile
        os.makedirs(os.path.dirname(logfile), exist_ok=True)

    def _emit(self, level: str, msg: str, **fields: Any) -> None:
        rec = {
            "ts": dt.datetime.utcnow().isoformat() + "Z",
            "level": level,
            "msg": msg,
            **fields,
        }
        line = json.dumps(rec, ensure_ascii=False)
        # ファイル
        with open(self.logfile, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        # コンソール
        sys.stderr.write(line + "\n")

    def info(self, msg: str, **fields: Any) -> None:
        self._emit("INFO", msg, **fields)

    def error(self, msg: str, **fields: Any) -> None:
        self._emit("ERROR", msg, **fields)


def read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    colmap = {
        "質問": "question",
        "question": "question",
        "回答": "observed_answer",
        "answer": "observed_answer",
        "正解": "gold",
        "correct": "gold",
    }
    rename = {}
    for c in df.columns:
        if c in colmap:
            rename[c] = colmap[c]
    df = df.rename(columns=rename)
    required = {"question", "observed_answer", "gold"}
    assert required.issubset(set(df.columns)), "CSVに質問/回答/正解の列が必要です"
    return df


def to_messages_for_responses(question: str, suppression_prompt: Optional[str]) -> List[Dict[str, Any]]:
    parts = lambda text: [{"type": "input_text", "text": text}]
    msgs: List[Dict[str, Any]] = []
    if suppression_prompt:
        msgs.append({"role": "system", "content": parts(suppression_prompt)})
    msgs.append({"role": "user", "content": parts(question)})
    return msgs


def to_messages_for_chat(question: str, suppression_prompt: Optional[str]) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = []
    if suppression_prompt:
        msgs.append({"role": "system", "content": suppression_prompt})
    msgs.append({"role": "user", "content": question})
    return msgs


def call_openai(
    client: OpenAI,
    model: str,
    question: str,
    suppression_prompt: Optional[str],
    logger: JsonLogger,
) -> str:
    resp_messages = to_messages_for_responses(question, suppression_prompt)
    chat_messages = to_messages_for_chat(question, suppression_prompt)

    # まず Responses API（推奨）。gpt-5対策として reasoning.effort=minimal を付与
    try:
        resp = client.responses.create(
            model=model,
            input=resp_messages,
            max_output_tokens=128,
            reasoning={"effort": "minimal"},
            text={"verbosity": "low"},
        )
        text = getattr(resp, "output_text", None)
        if text is None:
            # 念のためのフォールバック抽出
            try:
                chunks = []
                for item in getattr(resp, "output", []) or []:
                    if getattr(item, "type", "") == "message":
                        parts = getattr(item, "content", []) or []
                        for p in parts:
                            if getattr(p, "type", "") == "output_text":
                                chunks.append(p.text)
                text = "".join(chunks)
            except Exception:
                text = ""
        return (text or "").strip()
    except Exception as e:
        logger.error("Responses API failed; fallback to Chat Completions", error=str(e))

    # Chat Completions フォールバック
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=chat_messages,
            seed=42,
            max_completion_tokens=128,
        )
        text = resp.choices[0].message.content if resp.choices else ""
        return (text or "").strip()
    except Exception as e:
        logger.error("Chat Completions also failed", error=str(e))
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="入力CSV (質問/回答/正解)")
    ap.add_argument("--model", default="gpt-5", help="モデル名 (例: gpt-5, gpt-5-mini, gpt-4o)")
    ap.add_argument("--prompt-file", required=True, help="抑制プロンプト本文 (UTF-8)")
    ap.add_argument("--out", default="eval_results.csv", help="出力CSVパス")
    args = ap.parse_args()

    os.makedirs("logs", exist_ok=True)
    logger = JsonLogger(logfile=f"logs/eval_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.jsonl")
    logger.info("start", input=args.input, model=args.model, prompt_file=args.prompt_file)

    suppression_prompt = open(args.prompt_file, "r", encoding="utf-8").read().strip()
    df = read_csv(args.input)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    rows: List[Dict[str, Any]] = []
    for i, r in df.iterrows():
        q = str(r["question"]).strip()
        observed = str(r["observed_answer"]).strip()
        gold = str(r["gold"]).strip()

        out_plain = call_openai(client, args.model, q, suppression_prompt=None, logger=logger)
        out_supp = call_openai(client, args.model, q, suppression_prompt=suppression_prompt, logger=logger)

        rows.append({
            "質問": q,
            "回答(観測)": observed,
            "正解": gold,
            "プロンプトなし出力": out_plain,
            "プロンプトあり出力": out_supp,
        })

        logger.info(
            "asked",
            index=int(i),
            question_preview=q[:80],
            plain_preview=(out_plain or "")[:80],
            supp_preview=(out_supp or "")[:80],
        )

    out_df = pd.DataFrame(rows)
    out_df.to_csv(args.out, index=False, encoding="utf-8")
    logger.info("done", output=args.out, rows=len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
