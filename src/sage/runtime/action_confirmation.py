"""Owner-bound, immutable proposals for explicitly confirmed effects.

Preparing/cancelling never executes the effect. Approval atomically seals the
payload; the consumer must execute with action_id as its durable idempotency key.
An approved action cannot be cancelled as if it were an unsubmitted draft.
"""
import hashlib
import json
import time
from uuid import uuid4


class ConfirmationError(ValueError):
    pass


class ActionConfirmations:
    def __init__(self, store, *, namespace, clock=time.time):
        if not isinstance(namespace, str) or not namespace or namespace != namespace.strip():
            raise ConfirmationError("confirmation_namespace_required")
        self.store, self.namespace, self.clock = store, namespace, clock

    def _slot(self, owner, action_id):
        if not isinstance(owner, str) or not owner.strip() or owner != owner.strip():
            raise ConfirmationError("verified_owner_required")
        if not isinstance(action_id, str) or not action_id or len(action_id) > 128:
            raise ConfirmationError("invalid_action_id")
        return ("sage-action-confirmations-v1", self.namespace,
                hashlib.sha256(json.dumps([owner, action_id]).encode()).hexdigest())

    def prepare(self, owner, payload, *, operation_id=None, ttl_seconds=900):
        if operation_id is not None and (not isinstance(operation_id, str) or not operation_id or operation_id != operation_id.strip()):
            raise ConfirmationError("confirmation_operation_identity_required")
        action_id = hashlib.sha256(json.dumps([owner, operation_id]).encode()).hexdigest() if operation_id else uuid4().hex
        slot = self._slot(owner, action_id)
        payload = json.loads(json.dumps(payload, allow_nan=False))
        if not 0 < ttl_seconds <= 86400:
            raise ConfirmationError("invalid_confirmation_expiry")
        proposal = dict(action_id=action_id, payload=payload, status="pending",
                        expires_at=self.clock() + ttl_seconds)

        def prepare(values):
            current = values[slot]
            if current is not None and current["payload"] != payload:
                raise ConfirmationError("confirmation_payload_conflict")
            return {slot: current or proposal}

        return json.loads(json.dumps(self.store.update_many((slot,), prepare)[slot]))

    def resolve(self, owner, action_id, *, decision):
        if decision not in {"confirm", "cancel"}:
            raise ConfirmationError("explicit_confirmation_decision_required")
        slot = self._slot(owner, action_id)

        def resolve(values):
            current = values[slot]
            if current is None:
                raise ConfirmationError("confirmation_not_found")
            target = "confirmed" if decision == "confirm" else "cancelled"
            if current["status"] == target:
                return {slot: current}
            if current["status"] != "pending":
                raise ConfirmationError("confirmation_already_" + current["status"])
            if current["expires_at"] <= self.clock() and decision == "confirm":
                raise ConfirmationError("confirmation_expired")
            return {slot: {**current, "status": target}}

        return json.loads(json.dumps(self.store.update_many((slot,), resolve)[slot]))
