---
name: tax-report
description: "Sort journal trades into Indian tax buckets for a financial year: speculative intraday income, F&O business income, short-term and long-term capital gains, with turnover by the ICAI method. Use when the user asks about tax on trading, ITR, turnover or audit."
---

# Tax Report

## Workflow

`dd.py tax --fy 2026` covers April 2026 to March 2027. Add `--include-paper` to preview with paper trades.

## Output

Per bucket: trades, net P&L, charges and turnover, with how each bucket is taxed.

## Always say

This is an estimate from the journal to take to a chartered accountant. It is not a tax computation or a filing, the journal may not match the broker's tradebook, and rules changed with the Income-tax Act 2025.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
