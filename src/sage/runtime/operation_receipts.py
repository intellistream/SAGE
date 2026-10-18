"""Atomic, replayable local state effects, not an external exactly-once API.

The transition is pure: it may only compute replacements for declared slots.
Do not send email, call services, write files or call storage from a transition.
Durability requires a persistent state backend. The caller supplies a trusted,
owner-scoped operation identity and reauthorizes every invocation, including
replay. Receipts retain results indefinitely; this object does not own its store.
"""

import hashlib
import json
from collections.abc import Mapping


class OperationConflict(ValueError):
    """An existing operation identity was reused for different input or slots."""


class _Replay(Exception):
    def __init__(self, result):
        self.result = result


def _name(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("operation_identifier_must_be_nonempty_and_trimmed")
    return value


def _json(value):
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


class OperationReceipts:
    def __init__(self, store, *, namespace):
        self._store = store
        self.namespace = _name(namespace)

    def commit(self, operation_id, *, inputs, slots, transition, guard=None):
        """Commit destination replacements and immutable result in one transaction.

        transition(detached_values) returns (JSON_result, replacement_mapping).
        It runs only when the receipt is absent, under the state transaction.
        Conflicts/failures publish neither destination nor receipt. Replay aborts
        the read transaction and returns the saved result without touching current
        destination state (which may legitimately have changed since first commit).
        An optional same-store PreparedLeaseGuard is checked even for replay.
        This cannot fence operations in another database or external service.
        """
        receipt_slot = ("sage-operation-receipts-v1", self.namespace, _name(operation_id))
        slots = tuple(slots)
        if not slots or any(not isinstance(slot, tuple) or len(slot) != 3
                            or any(not isinstance(part, str) or not part or part != part.strip()
                                   for part in slot) for slot in slots):
            raise ValueError("operation_requires_explicit_state_slots")
        if len(set(slots)) != len(slots) or any(slot[0] == receipt_slot[0] for slot in slots):
            raise ValueError("operation_slots_duplicate_or_reserved")
        identity = hashlib.sha256(_json(inputs).encode()).hexdigest()
        destinations = [list(slot) for slot in sorted(slots)]
        all_slots = (*slots, receipt_slot)
        if guard is not None:
            guard.validate_store(self._store)
            if guard.slot in all_slots:
                raise ValueError("operation_guard_destination_overlap")
            all_slots = (*all_slots, guard.slot)

        def apply(values):
            if guard is not None:
                guard.apply(values)
            receipt = values[receipt_slot]
            if receipt is not None:
                if (not isinstance(receipt, dict) or receipt.get("version") != 1
                        or set(receipt) != {"version", "input_digest", "destinations", "result"}):
                    raise ValueError("invalid_operation_receipt")
                if receipt["input_digest"] != identity or receipt["destinations"] != destinations:
                    raise OperationConflict("operation_input_or_destination_conflict")
                raise _Replay(json.loads(_json(receipt["result"])))
            result, replacements = transition({slot: values[slot] for slot in slots})
            if not isinstance(replacements, Mapping) or set(replacements) != set(slots):
                raise ValueError("operation_destination_slots_mismatch")
            result = json.loads(_json(result))
            return {**values, **replacements, receipt_slot: {
                "version": 1, "input_digest": identity,
                "destinations": destinations, "result": result,
            }}

        try:
            saved = self._store.update_many(all_slots, apply)
        except _Replay as replay:
            return replay.result
        return saved[receipt_slot]["result"]
