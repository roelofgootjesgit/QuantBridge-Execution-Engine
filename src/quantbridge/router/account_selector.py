from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from quantbridge.accounts.account_policy import AccountPolicy
from quantbridge.accounts.account_state_machine import AccountStateMachine


@dataclass(frozen=True)
class AccountSelection:
    account_id: str
    reason: str
    selected_policy: AccountPolicy
    skipped: list[dict]


class AccountSelector:
    """Choose an eligible account while respecting status and policy filters."""

    def __init__(self, state_machine: AccountStateMachine) -> None:
        self.state_machine = state_machine

    def select(
        self,
        *,
        policies: Iterable[AccountPolicy],
        instrument: str,
        unhealthy_account_ids: Iterable[str] | None = None,
    ) -> AccountSelection | None:
        unhealthy = {str(account_id) for account_id in (unhealthy_account_ids or [])}
        instrument_key = str(instrument).upper()
        skipped: list[dict] = []

        ordered = sorted(policies, key=lambda p: p.priority)
        for policy in ordered:
            account_id = str(policy.account_id)
            if not policy.enabled:
                skipped.append({"account_id": account_id, "reason": "policy_disabled"})
                continue
            if account_id in unhealthy:
                skipped.append({"account_id": account_id, "reason": "broker_unhealthy"})
                continue
            if policy.allowed_symbols and instrument_key not in {sym.upper() for sym in policy.allowed_symbols}:
                skipped.append({"account_id": account_id, "reason": "symbol_not_allowed"})
                continue
            if not self.state_machine.is_eligible_for_trading(account_id=account_id, default_status=policy.mode):
                state = self.state_machine.get_state(account_id=account_id, default_status=policy.mode)
                skipped.append({"account_id": account_id, "reason": f"state_{state.status}"})
                continue
            return AccountSelection(
                account_id=account_id,
                reason="eligible_highest_priority",
                selected_policy=policy,
                skipped=skipped,
            )
        return None

