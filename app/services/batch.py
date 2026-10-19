"""Background batch screening jobs."""

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from app.services.auth import get_supabase_client
from app.services.scoring import screen_transaction


# Module-level executor. Initialized from create_app so tests do not spawn
# background threads unless explicitly requested.
_executor: Optional[ThreadPoolExecutor] = None


def init_batch_worker(max_workers: int = 4) -> ThreadPoolExecutor:
    """Initialize the background batch worker pool."""
    global _executor
    if _executor is None or _executor._shutdown:  # type: ignore[attr-defined]
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor


def get_executor() -> Optional[ThreadPoolExecutor]:
    return _executor


def shutdown_batch_worker(wait: bool = True) -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=wait)
        _executor = None


def submit_batch(
    batch_id: str,
    transactions: List[Dict[str, Any]],
    user_token: str,
) -> None:
    """Submit a batch screening job to the background worker."""
    executor = get_executor()
    if executor is None:
        raise RuntimeError("Batch worker has not been initialized")
    executor.submit(_run_batch, batch_id, transactions, user_token)


def _run_batch(
    batch_id: str,
    transactions: List[Dict[str, Any]],
    user_token: str,
) -> None:
    """Screen every transaction and update the batch record in Supabase."""
    client = get_supabase_client(user_token)
    if client is None:
        return

    total = len(transactions)
    _update_batch(
        client,
        batch_id,
        {"status": "running", "total": total, "processed": 0},
    )

    results: List[Dict[str, Any]] = []
    succeeded = 0
    failed = 0

    for index, tx in enumerate(transactions):
        try:
            result = screen_transaction(tx, user_token=user_token)
            results.append(result)
            succeeded += 1
        except Exception as exc:
            failed += 1
            results.append(
                {
                    "transaction_id": tx.get("transactionId"),
                    "error": str(exc),
                    "ok": False,
                }
            )

        processed = index + 1
        if processed % max(1, total // 10) == 0 or processed == total:
            _update_batch(
                client,
                batch_id,
                {
                    "processed": processed,
                    "succeeded": succeeded,
                    "failed": failed,
                    "results": json.loads(json.dumps(results, default=str)),
                },
            )

    final_status = "completed" if failed == 0 else "failed"
    _update_batch(
        client,
        batch_id,
        {
            "status": final_status,
            "processed": total,
            "succeeded": succeeded,
            "failed": failed,
            "results": json.loads(json.dumps(results, default=str)),
        },
    )


def _update_batch(client, batch_id: str, fields: Dict[str, Any]) -> None:
    try:
        client.table("batches").update(fields).eq("id", batch_id).execute()
    except Exception:
        # Best-effort progress update; failures are surfaced via final status.
        pass
