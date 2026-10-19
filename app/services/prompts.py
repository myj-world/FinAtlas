PROMPT_VERSION = "v1"

SCREENING_PROMPT_TEMPLATE = """You are an AI assistant supporting an anti-money laundering (AML) investigation.
Analyze the transaction below and return a JSON object with exactly these keys:
- updated_risk_score: a number between 0.0 and 1.0
- confidence: a number between 0.0 and 1.0
- reasoning: a concise explanation of the risk factors and any mitigating context
- false_positive_assessment: an evaluation of whether the name match is likely a false positive

The deterministic rule engine has already evaluated this transaction. Use that score as a baseline.
Add or refine risk based on context, unusual patterns, misspellings, multilingual name variants, and sanctions-list semantics.
Do not invent facts that are not supported by the input. Frame all conclusions as investigative indicators, not legal findings.

Prompt version: {version}

Transaction details:
{transaction_summary}

Deterministic score and matched rules:
{deterministic_summary}

Respond with only valid JSON.
"""


def build_screening_prompt(transaction: dict, deterministic_score: float, rules: list, hits: list) -> str:
    tx_summary = "\n".join(f"{k}: {v}" for k, v in transaction.items())
    rule_summary = "\n".join(
        f"- {rule['rule']}: +{rule['weight']} (score now {rule['cumulative_score']})"
        for rule in rules
    ) or "No deterministic rules matched."
    hit_summary = "\n".join(
        f"- {hit['list']}: matched '{hit['matched_name']}'" for hit in hits
    ) or "No sanctions hits."

    deterministic_summary = (
        f"Deterministic score: {deterministic_score}\n"
        f"Sanctions hits:\n{hit_summary}\n"
        f"Rules applied:\n{rule_summary}"
    )

    return SCREENING_PROMPT_TEMPLATE.format(
        version=PROMPT_VERSION,
        transaction_summary=tx_summary,
        deterministic_summary=deterministic_summary,
    )
