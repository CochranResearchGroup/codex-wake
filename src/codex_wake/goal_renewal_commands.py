"""Public renewal adapters. Native MCP may propose/consume; it cannot approve."""

import json
from pathlib import Path

from .goal_renewal import propose, apply, _now, RenewalError
from .goal_supervision import verified_native_caller
from .permission_enforcement import cli_principal, verified_tasks
from .session_permissions import Principal
from .records import WakeError


def execute(
    verb, arguments, root, policy, *, principal, native_context=None, mcp=False
):
    thread = arguments["caller_thread_id"]
    if mcp:
        verified_native_caller(native_context, thread)
        if (
            principal.role == "operator"
            or arguments.get("approve")
            or arguments.get("apply")
        ):
            raise RenewalError(
                "renewal_operator_required",
                "native model callers cannot approve a renewal",
            )
    if verb == "apply-renewal":
        return apply(
            root,
            policy,
            thread,
            arguments["proposal_id"],
            principal=principal,
            expected_fingerprint=arguments["fingerprint"],
            explicit=arguments.get("approve", False),
        )
    if verb not in ("extend", "reset"):
        raise RenewalError("renewal_invalid", "unsupported renewal action")
    options = {
        key: arguments[key]
        for key in (
            "operation_id",
            "token_limit",
            "deadline",
            "remaining_seconds",
            "expires_at",
            "shared",
            "resume",
            "task_id",
        )
        if arguments.get(key) is not None
    }
    options.setdefault("expires_at", _now() + 300)
    result = propose(root, policy, thread, principal=principal, mode=verb, **options)
    if arguments.get("apply"):
        return apply(
            root,
            policy,
            thread,
            result["proposal_id"],
            principal=principal,
            expected_fingerprint=result["fingerprint"],
            explicit=True,
        )
    return result


def register_parser(commands):
    """Call with the existing goal-limits command subparser, not the root parser."""
    for verb in ("extend", "reset", "apply-renewal"):
        parser = commands.add_parser(
            verb,
            help=(
                "apply an exact approved proposal; never self-authorize"
                if verb == "apply-renewal"
                else verb
                + " external budget through a qualified operator proposal; preserves lifetime history"
            ),
        )
        parser.add_argument("--policy", type=Path, required=True)
        parser.add_argument("--caller-thread-id", required=True)
        parser.add_argument("--bus-root", type=Path, required=True)
        parser.add_argument("--operator-capability", type=Path)
        parser.add_argument("--actor-capability", type=Path)
        parser.add_argument("--app-server", default="unix://")
        parser.add_argument("--task-id")
        parser.add_argument("--assignment-id")
        parser.add_argument("--operation-id", required=verb != "apply-renewal")
        parser.add_argument("--json", dest="as_json", action="store_true")
        if verb == "apply-renewal":
            parser.add_argument("--proposal-id", required=True)
            parser.add_argument("--fingerprint", required=True)
            parser.add_argument(
                "--approve",
                action="store_true",
                help="authenticated explicit operator acceptance; does not ask again",
            )
        else:
            parser.add_argument(
                "--token-limit",
                type=int,
                required=True,
                help="new absolute window ceiling, not extra tokens",
            )
            deadline = parser.add_mutually_exclusive_group(required=True)
            deadline.add_argument(
                "--deadline", type=float, help="absolute UTC epoch seconds"
            )
            deadline.add_argument(
                "--remaining-seconds",
                type=int,
                help="explicit new remaining-time grant from qualified proposal time",
            )
            parser.add_argument(
                "--expires-at",
                type=float,
                help="absolute proposal expiry; defaults to five minutes",
            )
            parser.add_argument(
                "--shared",
                action="store_true",
                help="explicitly authorizes the displayed complete shared-allocation member set",
            )
            parser.add_argument(
                "--resume",
                action="store_true",
                help="approve resume after fresh first-poll acknowledgement; otherwise leaves paused",
            )
            parser.add_argument(
                "--apply",
                action="store_true",
                help="authenticated explicit directive applies this exact proposal without another confirmation",
            )


def command(args, root):
    try:
        principal = cli_principal(args, root)
        arguments = {
            key: value
            for key, value in vars(args).items()
            if key
            in (
                "caller_thread_id",
                "operation_id",
                "token_limit",
                "deadline",
                "remaining_seconds",
                "expires_at",
                "shared",
                "resume",
                "task_id",
                "proposal_id",
                "fingerprint",
                "approve",
                "apply",
            )
            and value is not None
        }
        result = execute(
            args.goal_limits_command, arguments, root, args.policy, principal=principal
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, WakeError) as error:
        print(
            json.dumps(
                dict(
                    state="held",
                    error=dict(
                        code=getattr(error, "code", "renewal_unavailable"),
                        message=str(error),
                    ),
                )
            )
        )
        return 2


def tool_specs():
    from .harness_mcp import CALLER, TEXT

    number = {"type": "number", "exclusiveMinimum": 0}
    integer = {"type": "integer", "minimum": 1}
    flag = {"type": "boolean"}
    result = {}
    for verb in ("extend", "reset"):
        result["wake_goal_limits_" + verb] = (
            "goal-renewal",
            verb,
            "Propose an exact "
            + verb
            + " of external budget. This grants nothing: authenticated operator acceptance "
            "in the common attention queue is required. Extend preserves spend; reset retains lifetime/native history. "
            "Specify absolute UTC epoch deadline or explicit remaining_seconds. Native goal resume alone grants no allowance.",
            dict(
                caller_thread_id=CALLER,
                operation_id=TEXT,
                token_limit=integer,
                deadline=number,
                remaining_seconds=integer,
                expires_at=number,
                shared=flag,
                resume=flag,
                task_id=TEXT,
                assignment_id=TEXT,
            ),
            ["caller_thread_id", "operation_id", "token_limit"],
            False,
        )
    result["wake_goal_limits_apply_renewal"] = (
        "goal-renewal",
        "apply-renewal",
        "Apply only an already authenticated exact operator response. Models cannot approve or increase their own allowance. "
        "Retry the same proposal to reconcile, including an approved resume awaiting first watcher poll.",
        dict(
            caller_thread_id=CALLER,
            proposal_id=TEXT,
            fingerprint=TEXT,
            task_id=TEXT,
            assignment_id=TEXT,
        ),
        ["caller_thread_id", "proposal_id", "fingerprint"],
        False,
    )
    return result


def mcp_call(runner, verb, arguments, native_context):
    root = (
        runner.goal_limits_root
        if runner.goal_limits_root is not None
        else runner.wake_root
    )
    if root is None or runner.goal_limits_policy is None:
        raise RenewalError(
            "renewal_host_scope_unavailable", "configured goal-limit scope required"
        )
    thread = arguments["caller_thread_id"]
    verified_native_caller(native_context, thread)
    from .harness_mcp import controller_tasks

    tasks = verified_tasks(
        root,
        thread,
        arguments.get("task_id"),
        arguments.get("assignment_id"),
        controller_tasks=controller_tasks(runner, thread),
    )
    return execute(
        verb,
        arguments,
        root,
        runner.goal_limits_policy,
        principal=Principal(thread, tasks=tasks),
        native_context=native_context,
        mcp=True,
    )
