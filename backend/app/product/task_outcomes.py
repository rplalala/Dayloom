"""Safe typed terminal outcomes, independent of HTTP and private provider failures."""

from backend.app.integrations.google.common import ProviderResponseError
from backend.app.integrations.http import ProviderHTTPError
from backend.app.llm.client import StructuredOutputError
from backend.app.policies.preference_input import MESSAGES
from backend.app.policies.requirement_feedback import ACQUISITION_FAILURES
from backend.app.policies.requirement_feedback import MESSAGES as REQUIREMENT_MESSAGES
from backend.app.runtime.budget import ToolBudgetExceededError
from backend.app.schemas.poi_semantics import SemanticPreparationLimit
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
from backend.app.services.generation_resources import GenerationResourceError
from backend.app.services.planning import PlanningNeedsClarificationError
from backend.app.services.product_presentation import public_clarification


def failure_outcome(error):
    if isinstance(error, PlanningNeedsClarificationError):
        if error.issues.get("code") == "unsupported_hard_requirements":
            message, action = REQUIREMENT_MESSAGES["unsupported_hard_requirements"]
            return "needs_clarification", {
                "code": "unsupported_hard_requirements",
                "message": message,
                "action": action,
                "issues": public_clarification(error.issues),
            }
        if error.issues.get("code") in ACQUISITION_FAILURES:
            return "failed", {
                "code": "requirements_unmet",
                "message": (
                    "The planner could not meet your requirements with the available options."
                ),
                "action": "Your original requirements have been kept.",
                "issues": public_clarification(error.issues),
            }
        if error.issues.get("safety_disposition") == "SAFETY_BLOCK":
            types = {issue["issue_type"] for issue in error.issues["issues"]}
            kind = "safety_self_harm" if "safety_self_harm" in types else "safety_serious_harm"
            message, action = MESSAGES[kind]
            return "safety_blocked", {
                "code": "safety_blocked",
                "message": message,
                "action": action,
            }
        return "needs_clarification", {
            "code": "needs_clarification",
            "message": "Please clarify your travel preferences.",
            "action": "Review your brief before generating again.",
            "issues": public_clarification(error.issues),
        }
    seen = set()
    cause = error
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if isinstance(cause, RequirementBoundaryError) and cause.provider_content_filtered:
            return "provider_blocked", {
                "code": "provider_blocked",
                **cause.public_provider_action(),
            }
        code = None
        if (
            isinstance(cause, SemanticPreparationLimit)
            and str(cause) == "required_primary_role_not_qualified"
        ):
            code, message = (
                "requirements_unmet",
                "The available place evidence could not verify all required visits.",
            )
        elif isinstance(
            cause, (ToolBudgetExceededError, GenerationResourceError, SemanticPreparationLimit)
        ):
            code, message = (
                "planning_resource_limit",
                "Planning reached its configured resource limit.",
            )
        elif isinstance(cause, TimeoutError):
            code, message = "planning_timeout", "Planning ran out of time."
        elif isinstance(cause, (ProviderHTTPError, ProviderResponseError, StructuredOutputError)):
            code, message = (
                "provider_unavailable",
                "A planning provider could not return a usable result.",
            )
        if code:
            return "failed", {
                "code": code,
                "message": message,
                "action": (
                    "Your original requirements have been kept. "
                    "You can try again without changing them."
                ),
            }
        cause = cause.__cause__
    return "failed", {
        "code": "planning_failed",
        "message": "The itinerary could not be generated.",
        "action": (
            "Your original requirements have been kept. "
            "You can try again without changing them."
        ),
    }
