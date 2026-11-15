# Working in this repo

- Python standard library only. Do not add dependencies.
- Every command goes through `dd.py` and prints JSON. Skills call commands; they hold no logic.
- Rules that change (charges, lots, holidays, ticks) live in `dalal/refdata.py` with dates. Never hard-code them elsewhere or in a SKILL.md.
- Safety behaviour is tested. Any change to `risk.py`, `ticket.py` or `hooks/order_guard.py` needs a test.
- Run `python3 -m unittest discover -s tests -v` before committing. Tests are offline and use `DALAL_NOW` to fix the clock.
- A skill's frontmatter `name` must equal its folder name, and `description` must be double-quoted.
- Never commit `.env`, `config.json` or `trader/`.
