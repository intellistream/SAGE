# Independent dependency verification

`sage.runtime.dependency_verifier.DependencyVerifier` uses the existing
`WorkJournal` and `WorkService` for independent readiness checks. It does not
create another scheduler. The application can expose its otherwise-ready web
service while a separate integration remains unavailable.

```python
from sage.runtime.dependency_verifier import DependencyRejected, DependencyVerifier

def verify_identity():
    # Read-only network call with bounded transport timeouts. Keep credentials
    # inside this closure; never include them in the name or return value.
    identity = client.authenticate()
    if identity.workspace_id != expected_workspace:
        raise DependencyRejected("workspace_mismatch")
    return True

dependency = DependencyVerifier(state, name="workspace-integration", probe=verify_identity)
dependency.start()  # Commits pending state, does not await the network probe.
if dependency.ready():
    accept_integration_requests()
dependency.close()  # Drain BEFORE closing the borrowed state or network client.
```

Only the exact boolean `True` verifies. Any other return value, or an explicit
`DependencyRejected`, permanently rejects this binding. Other exceptions retry
through the native work failure policy, initially after one second, exponentially
up to sixty seconds. Retry and poll bounds are configurable. The journal retains
only generated binding IDs, fixed result statuses and `dependency_unavailable`;
it never persists probe responses or exception messages. Callers must still avoid
logging secrets themselves and use non-secret dependency names.

Each new verifier captures a fresh process binding. Restart must construct and
start a fresh instance even when historical state says verified. A historical
success is never sufficient to unlock current credentials. A replacement cancels
obsolete pending/running checks without deleting their audit records. Native
lease fencing and same-store completion transforms prevent an old worker's late
success from unlocking a newer binding. Registration and pending intent commit
atomically; a lost acknowledgement can replay the same instance without resetting
success. Delayed registration cannot overwrite a binding registered since that
instance was constructed.

There is one authoritative binding per dependency name in a state store. Use
distinct names for replicas or tenants needing independent readiness. Configuration
is immutable for one binding: capture it in the probe; replace the verifier on
change, and reject requests if application configuration no longer matches that
binding. Checks are read-only: leases do not fence irreversible external effects.

This is startup verification, not continuous authentication or an uptime monitor.
An integration must still authorize every request and handle later transport or
credential revocation failures. Closing immediately makes local readiness false;
shutdown timeout does not abandon the active probe or permit closing its store.
Storage/supervisor faults remain errors, not fabricated successful checks.

Acceptance covers real SQLite storage, blocked probes and safe draining, transient
recovery, permanent rejection, malformed results, historical success, overlapping
bindings, lost registration acknowledgements and actual process death immediately
after the pending transaction commits.
