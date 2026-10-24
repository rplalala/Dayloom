"""Safe typed terminal outcomes, independent of HTTP and private provider failures."""

from backend.app.policies.preference_input import MESSAGES
from backend.app.policies.requirement_feedback import ACQUISITION_FAILURES
from backend.app.policies.requirement_feedback import MESSAGES as REQUIREMENT_MESSAGES
from backend.app.schemas.requirement_boundary import RequirementBoundaryError
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
    cause = error.__cause__
    if isinstance(cause, RequirementBoundaryError) and cause.provider_content_filtered:
        return "provider_blocked", {"code": "provider_blocked", **cause.public_provider_action()}
    return "failed", {
        "code": "planning_timeout" if isinstance(error, TimeoutError) else "planning_failed",
        "message": "The itinerary could not be generated.",
        "action": "Review your brief and explicitly try again.",
    }
