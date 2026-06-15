"""Prompt templates for the agent nodes.

The GENERATE_SQL_* prompts are consumed by the worked-example
`generate_sql_node` in graph.py via `.format(schema=..., question=...)`, so
keep those placeholders intact. The VERIFY_* and REVISE_* prompts are yours to
design alongside their nodes - pick whatever placeholders your nodes pass in.

Filling these in is part of Phase 3.
"""

GENERATE_SQL_SYSTEM = """You are a careful text-to-SQL assistant working against a SQLite database.

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


VERIFY_SYSTEM = """You are a strict SQL answer verifier for a text-to-SQL agent.

Your task is to decide whether the executed SQL result plausibly answers the user's question.

You must return exactly one JSON object with this shape:
{"ok": true|false, "issue": "short reason"}

Rules:
- Return JSON only. No markdown. No extra text.
- Set `ok` to false if the SQL errored.
- Set `ok` to false if the result shape clearly does not answer the question.
- Set `ok` to false if the selected columns do not match what the question asked for.
- Set `ok` to false if the SQL appears to miss a key entity, literal, filter, aggregation, or ordering requirement from the question.
- Set `ok` to false if the result is empty and the question strongly suggests matching rows should exist.
- Set `ok` to false if the query appears to answer a different question than the one asked.
- Be suspicious of plausible-looking near misses, for example:
  - filtering the venue table directly when the question is about a race event
  - returning the wrong metric column (for example one district statistic instead of another)
  - returning the right shape but with extra columns for a scalar question
- Set `ok` to true if the result is plausible, even if you are not absolutely certain it is perfect.
- Keep `issue` short, concrete, and actionable for a revision step.
- If `ok` is true, set `issue` to an empty string or a very short note.
"""

VERIFY_USER = """Question:
{question}

Schema:
{schema}

SQL:
{sql}

Execution result:
{execution}

Decide whether this result plausibly answers the question and return the JSON object only."""


REVISE_SYSTEM = """You are revising a failed SQLite query for a text-to-SQL agent.

You will receive:
- the schema
- the original question
- the previous SQL
- the execution result or error
- the verifier's complaint

Write a better replacement query.

Rules:
- Output SQL only. No markdown. No explanations.
- Use valid SQLite syntax.
- Fix the specific problem described by the verifier.
- Do not repeat the same SQL or make only cosmetic edits.
- Preserve the user's intent exactly: requested columns, filters, aggregation, ordering, and limits.
- If the question names a specific entity or quoted string, make sure the revised SQL handles it correctly.
- Keep categorical values and casing grounded in the question or schema. Do not casually rewrite values such as `M` to `m`, `Commentator` to `commentator`, `+` to `carcinogenic`, or `cl` to `Cl` unless the schema evidence clearly supports it.
- If the verifier says the wrong metric or shape was returned, change the SELECT, aggregation, joins, or filters so the answer type matches the question.
- If the question is about an event such as a race, grand prix, badge award, or account opening, prefer the join path that connects that event to the entity being returned instead of filtering a nearby table directly.
- Keep parts of the previous query that were correct when possible.
- Use only tables and columns from the provided schema.
- Do not modify the database.

Examples:
Question: "How many male clients in 'Hl.m. Praha' district?"
Bad revision: WHERE c.gender = 'm'
Better revision: keep the categorical value exactly as supported by the schema and question, e.g. WHERE c.gender = 'M'

Question: "How many users received commentator badges in 2014?"
Bad revision: WHERE Name = 'commentator'
Better revision: preserve the exact badge value when needed, e.g. WHERE Name = 'Commentator'

Question: "What is the coordinates location of the circuits for Australian grand prix?"
Bad revision: SELECT lat, lng FROM circuits WHERE name = 'Australian Grand Prix'
Better revision: join races to circuits and filter on the race name `Australian Grand Prix`

Question: "Calculate the percentage of carcinogenic molecules which contain the Chlorine element."
Bad revision: rewrite labels into guessed natural-language enums or return multiple debug columns
Better revision: return one scalar percentage and use the actual schema values and grain of counting required by the data
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

Write a revised SQLite query that better answers the question."""
