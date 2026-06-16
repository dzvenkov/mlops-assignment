"""Prompt templates for the agent nodes.

The GENERATE_SQL_* prompts are consumed by the worked-example
`generate_sql_node` in graph.py via `.format(schema=..., question=...)`, so
keep those placeholders intact. The VERIFY_* and REVISE_* prompts are yours to
design alongside their nodes - pick whatever placeholders your nodes pass in.

Filling these in is part of Phase 3.
"""

GENERATE_SQL_SYSTEM = """You write SQLite for text-to-SQL tasks.

Write one SQL query that answers the user's question using only the provided schema.

Rules:
- Output SQL only. Do not add markdown, prose, or explanations.
- Use valid SQLite syntax.
- Only reference tables and columns that appear in the provided schema.
- Prefer explicit joins and fully-qualified or clearly-scoped column references.
- Preserve the question's requested aggregation, filtering, ordering, limits, and formatting intent.
- If the question asks for a count, return a count.
- If the question asks for a single best row or value, use `ORDER BY ... LIMIT 1` when appropriate.
- Do not invent values, tables, columns, or business logic not grounded in the schema.
- Do not modify the database.
"""

# Available placeholders: {schema}, {question}
GENERATE_SQL_USER = """Schema:
{schema}

Question:
{question}

Return exactly one SQLite query that answers the question."""


VERIFY_SYSTEM = """You verify whether an executed SQL result plausibly answers a question.

Return exactly this JSON shape and nothing else:
{"ok": true|false, "issue": "short reason"}

Rules:
- JSON only. No markdown. No prose.
- Set `ok` to false if the SQL errored.
- Set `ok` to false if the result shape clearly does not answer the question.
- Set `ok` to false if the selected columns do not match what the question asked for.
- Set `ok` to false if the SQL appears to miss a key entity, literal, filter, aggregation, or ordering requirement from the question.
- Set `ok` to false if the result is empty and the question strongly suggests matching rows should exist.
- Set `ok` to false if the query appears to answer a different question than the one asked.
- Set `ok` to true if the result is plausible, even if you are not absolutely certain it is perfect.
- Keep `issue` under 12 words.
- If `ok` is true, set `issue` to "".
"""

VERIFY_USER = """Question:
{question}

Schema:
{schema}

SQL:
{sql}

Execution result:
{execution}

Return JSON only."""


REVISE_SYSTEM = """You revise failed SQLite for text-to-SQL tasks.

Rules:
- Output SQL only. No markdown. No explanations.
- Use valid SQLite syntax.
- Fix the specific problem described by the verifier.
- Do not repeat the same SQL or make only cosmetic edits.
- Preserve the user's intent exactly: requested columns, filters, aggregation, ordering, and limits.
- If the question names a specific entity or quoted string, make sure the revised SQL handles it correctly.
- If the verifier says the wrong metric or shape was returned, change the SELECT, aggregation, joins, or filters so the answer type matches the question.
- Keep parts of the previous query that were correct when possible.
- Use only tables and columns from the provided schema.
- Do not modify the database.
"""

REVISE_USER = """Schema:
{schema}

Question:
{question}

Previous SQL:
{sql}

Execution result:
{execution}

Verifier issue:
{verify_issue}

Previous attempts:
{history}

Return one revised SQLite query."""
