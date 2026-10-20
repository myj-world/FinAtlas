PROMPT_VERSION = "v2"

SCREENING_PROMPT_TEMPLATE = """You are an AI assistant supporting an anti-money laundering (AML) investigation.
Analyze the transaction below and return a JSON object with exactly these keys:
- updated_risk_score: a number between 0.0 and 1.0
- unusual_pattern_detected: a boolean indicating whether the supplied transaction data shows an unusual pattern
- confidence: a number between 0.0 and 1.0
- reasoning: a concise explanation of the risk factors and any mitigating context
- false_positive_assessment: an evaluation of whether the name match is likely a false positive

The deterministic rule engine has already evaluated this transaction. Use its score as the baseline.
Apply these exact cumulative weights, capped at 1.0:
- Direct sanctions match: +0.30
- Large transaction above $1,000 USD equivalent: +0.05
- High-risk sender or receiver jurisdiction: +0.10
- Unusual transaction pattern detected by you: +0.55
Set unusual_pattern_detected to true only when the supplied transaction data supports an unusual pattern.
The updated_risk_score must equal the deterministic score plus the applicable weights, capped at 1.0.
Review every transaction, including those with no deterministic rules matched.
Do not invent facts or imply transaction history that was not provided. Frame conclusions as investigative indicators, not legal findings.

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
