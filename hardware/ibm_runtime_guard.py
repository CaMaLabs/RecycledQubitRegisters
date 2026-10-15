#!/usr/bin/env python3
"""Fail-closed IBM Runtime submission guard.

Project policy: paid IBM Quantum Runtime is NOT authorized by default.

This module must be called immediately before any Sampler/Estimator/QPU
submission.  It verifies the service's *currently active* instance against
service.instances() and allows submission only when the exact active instance
is identified as plan == "open".

Why the check happens immediately before submission:
- backend()/backends()/job()/jobs() can change QiskitRuntimeService's active
  instance when several instances are available;
- plans_preference=["open"] is a useful selector, but an explicit instance can
  override it;
- a saved credential or an attached credit card is not permission to spend.

Ambiguity is treated as a hard failure.  There is intentionally no paid-plan
override in this module.  If paid runtime is ever explicitly authorized, that
should be a separate reviewed code change.
"""
from __future__ import annotations

from typing import Any


class RuntimePlanGuardError(RuntimeError):
    """Raised when a free/open IBM Runtime instance cannot be proved."""


def _normalize_plan(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def runtime_plan_receipt(service, backend=None) -> dict:
    """Return a fail-closed receipt describing the active IBM Runtime instance."""
    try:
        active = service.active_instance()
    except Exception as exc:
        raise RuntimePlanGuardError(
            f"Cannot verify active IBM Runtime instance: {exc}"
        ) from exc

    if not active:
        raise RuntimePlanGuardError(
            "IBM Runtime active_instance() returned no instance; refusing submission."
        )

    # Selecting/reading the backend before this call is intentional because IBM's
    # service may change its active instance while resolving a backend.
    backend_name = None
    if backend is not None:
        backend_name = getattr(backend, "name", None)
        if callable(backend_name):
            try:
                backend_name = backend_name()
            except Exception:
                backend_name = None

    try:
        instances = service.instances()
    except Exception as exc:
        raise RuntimePlanGuardError(
            f"Cannot list IBM Runtime instances to verify billing plan: {exc}"
        ) from exc

    if not isinstance(instances, (list, tuple)):
        raise RuntimePlanGuardError(
            "IBM Runtime instances() did not return a list; refusing submission."
        )

    active_s = str(active)
    matches = []
    for row in instances:
        if not isinstance(row, dict):
            continue
        crn = str(row.get("crn") or "")
        name = str(row.get("name") or "")
        if active_s and active_s in {crn, name}:
            matches.append(row)

    if len(matches) != 1:
        raise RuntimePlanGuardError(
            "Could not uniquely match the active IBM Runtime instance to "
            "service.instances(); refusing submission."
        )

    row = matches[0]
    plan = _normalize_plan(row.get("plan"))
    receipt = {
        "active_instance": active_s,
        "instance_name": row.get("name"),
        "plan": row.get("plan"),
        "backend": backend_name,
        "open_plan_verified": plan == "open",
    }

    if plan != "open":
        raise RuntimePlanGuardError(
            "REFUSING QPU SUBMISSION: active IBM Runtime instance is not "
            f"verified Open Plan (plan={row.get('plan')!r}, "
            f"instance={row.get('name') or active_s!r}). "
            "Paid runtime is not authorized by project policy."
        )

    return receipt


def assert_open_plan_submission(service, backend=None) -> dict:
    """Verify and return the Open-Plan receipt, or raise before submission."""
    return runtime_plan_receipt(service, backend=backend)
