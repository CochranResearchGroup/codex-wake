"""Sanitized, effect-free planning for managed webhook secret rotation."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .github_source_config import GitHubSourceStore
from .managed_webhook_rotation import (
    ManagedWebhookRotationStore, PendingEffect, RotationPhase, RotationRecord,
)
from .managed_webhooks import LifecycleState, ManagedWebhookBinding, ManagedWebhookStore
from .webhook_lifecycle import WebhookListenerConfig, WebhookListenerStore, webhook_service_name


@dataclass(frozen=True, slots=True)
class RotationPreview:
    source_instance: str
    phase: str
    rotation_revision: int | None
    binding_revision: int
    previous_generation: int
    target_generation: int | None
    overlap_deadline: int | None
    deadline_state: str
    pending_effect: str
    next_action: str
    effect_boundary_required: bool
    target_delivery_proven: bool
    apply_supported: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "source_instance": self.source_instance,
            "phase": self.phase,
            "rotation_revision": self.rotation_revision,
            "binding_revision": self.binding_revision,
            "previous_generation": self.previous_generation,
            "target_generation": self.target_generation,
            "overlap_deadline": self.overlap_deadline,
            "deadline_state": self.deadline_state,
            "pending_effect": self.pending_effect,
            "next_action": self.next_action,
            "effect_boundary_required": self.effect_boundary_required,
            "target_delivery_proven": self.target_delivery_proven,
            "apply_supported": self.apply_supported,
        }


class ManagedWebhookRotationPreviewer:
    """Join local authorities without resolving a secret or contacting GitHub."""

    def __init__(self, wake_root: Path):
        self.wake_root = Path(wake_root).resolve()

    def preview(
        self, source_instance: str, *, now: int,
        target_generation: int | None = None, overlap_seconds: int | None = None,
    ) -> RotationPreview:
        if type(now) is not int or now < 0:
            raise ValueError("managed webhook rotation preview clock is invalid")
        if overlap_seconds is not None and (
            type(overlap_seconds) is not int or not 60 <= overlap_seconds <= 604_800
        ):
            raise ValueError("managed webhook rotation proposal is invalid")
        listener, binding = self._authority(source_instance)
        records = tuple(
            item for item in ManagedWebhookRotationStore(self.wake_root).records()
            if item.source_instance == source_instance
        )
        if len(records) > 1:
            raise ValueError("managed webhook rotation ownership is ambiguous")
        if not records:
            if listener.previous_generation is not None or binding.secret_generation != listener.current_generation:
                raise ValueError("managed webhook rotation authority is invalid")
            if target_generation is None:
                return RotationPreview(
                    source_instance, "NOT_STARTED", None, binding.generation,
                    listener.current_generation, None, None, "not_started", "NONE",
                    "PREPARE_ROTATION", False, False,
                )
            if (
                type(target_generation) is not int
                or not listener.current_generation < target_generation < 2**31
                or overlap_seconds is None
            ):
                raise ValueError("managed webhook rotation proposal is invalid")
            return RotationPreview(
                source_instance, "NOT_STARTED", None, binding.generation,
                listener.current_generation, target_generation, now + overlap_seconds,
                "proposed", "NONE", "PREPARE_ROTATION", False, False,
            )
        record = records[0]
        self._validate_current(listener, binding, record)
        if now < record.last_observed_at:
            raise ValueError("managed webhook rotation clock moved backwards")
        if target_generation is not None and target_generation != record.target_generation:
            raise ValueError("managed webhook rotation target conflicts with current authority")
        deadline_state = "terminal" if record.phase in {
            RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK,
        } else "expired" if now > record.overlap_deadline else "active"
        action = self._next_action(record, expired=deadline_state == "expired")
        effect_actions = {
            "TRANSITION_AND_RESTART_DUAL", "UPDATE_PROVIDER_ONCE",
            "TRANSITION_AND_RESTART_TARGET_ONLY", "RETIRE_PREVIOUS_SECRET",
            "ROLLBACK_REQUIRED",
        }
        return RotationPreview(
            source_instance=source_instance, phase=record.phase.value,
            rotation_revision=record.revision, binding_revision=record.binding_revision,
            previous_generation=record.previous_generation,
            target_generation=record.target_generation,
            overlap_deadline=record.overlap_deadline, deadline_state=deadline_state,
            pending_effect=record.pending_effect.value, next_action=action,
            effect_boundary_required=action in effect_actions,
            target_delivery_proven=record.delivery_locator is not None,
        )

    def _authority(self, source_instance: str) -> tuple[WebhookListenerConfig, ManagedWebhookBinding]:
        listener = WebhookListenerStore(self.wake_root).select(source_instance)
        source = GitHubSourceStore(self.wake_root).registry().select(source_instance)
        bindings = tuple(
            item for item in ManagedWebhookStore(self.wake_root).bindings()
            if item.source_instance == source_instance
        )
        if len(bindings) != 1:
            raise ValueError("managed webhook binding authority is unavailable")
        binding = bindings[0]
        if (
            binding.canonical_root != str(self.wake_root) or binding.owner_uid != os.getuid()
            or binding.service_id != webhook_service_name(source_instance)
            or binding.repository != source.repository or binding.repository_id != source.repository_id
            or binding.provider_host != "api.github.com" or source.hostname != "github.com"
            or binding.lifecycle is not LifecycleState.ACTIVE or binding.provider_hook_id is None
        ):
            raise ValueError("managed webhook rotation authority is invalid")
        return listener, binding

    def _validate_current(
        self, listener: WebhookListenerConfig, binding: ManagedWebhookBinding,
        record: RotationRecord,
    ) -> None:
        generations = (
            (listener.previous_generation, listener.current_generation)
            if listener.previous_generation is not None else (listener.current_generation,)
        )
        previous = (record.previous_generation,)
        dual = (record.previous_generation, record.target_generation)
        target = (record.target_generation,)
        if record.pending_effect is PendingEffect.ROLLBACK or record.phase in {
            RotationPhase.UNKNOWN, RotationPhase.EXPIRED,
        }:
            allowed = {previous, dual, target}
        elif record.phase is RotationPhase.PREPARED:
            allowed = {previous, dual} if record.pending_effect is PendingEffect.RESTART_DUAL else {previous}
        elif record.phase in {RotationPhase.DUAL_READY, RotationPhase.PROVIDER_PENDING}:
            allowed = {dual}
        elif record.phase is RotationPhase.AWAITING_DELIVERY:
            if record.pending_effect is PendingEffect.RESTART_TARGET_ONLY:
                allowed = {dual, target}
            elif record.runtime_proof is not None and record.runtime_proof.loaded_generations == target:
                allowed = {target}
            else:
                allowed = {dual}
        elif record.phase in {RotationPhase.RETIRING, RotationPhase.COMPLETE}:
            allowed = {target}
        else:
            allowed = {previous}
        if (
            record.owner_id != binding.owner_id
            or record.canonical_root != str(self.wake_root) or record.owner_uid != os.getuid()
            or record.service_id != binding.service_id or record.binding_revision != binding.generation
            or record.previous_generation != binding.secret_generation
            or generations not in allowed
        ):
            raise ValueError("managed webhook rotation authority is invalid")

    @staticmethod
    def _next_action(record: RotationRecord, *, expired: bool) -> str:
        if record.pending_effect is PendingEffect.ROLLBACK:
            return "OBSERVE_ROLLBACK_RESULT"
        if expired or record.phase in {RotationPhase.UNKNOWN, RotationPhase.EXPIRED}:
            return "ROLLBACK_REQUIRED"
        if record.phase in {RotationPhase.COMPLETE, RotationPhase.ROLLED_BACK}:
            return "NONE"
        if record.phase is RotationPhase.PREPARED:
            return (
                "TRANSITION_AND_RESTART_DUAL"
                if record.pending_effect is PendingEffect.RESTART_DUAL
                else "INTEND_DUAL_RESTART"
            )
        if record.phase is RotationPhase.DUAL_READY:
            return "INTEND_PROVIDER_UPDATE"
        if record.phase is RotationPhase.PROVIDER_PENDING:
            return "OBSERVE_PROVIDER_RESULT" if record.pending_effect is PendingEffect.PROVIDER_UPDATE else "BLOCKED"
        if record.phase is RotationPhase.AWAITING_DELIVERY:
            if record.pending_effect is PendingEffect.RESTART_TARGET_ONLY:
                return "TRANSITION_AND_RESTART_TARGET_ONLY"
            if record.delivery_locator is None:
                return "AWAIT_TARGET_DELIVERY"
            if record.runtime_proof is not None and record.runtime_proof.loaded_generations == (record.target_generation,):
                return "INTEND_RETIREMENT"
            return "INTEND_TARGET_RESTART"
        if record.phase is RotationPhase.RETIRING:
            return "RETIRE_PREVIOUS_SECRET"
        return "BLOCKED"
