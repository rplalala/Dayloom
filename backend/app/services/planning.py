"""Application services separating HTTP clients from research planners."""

from datetime import date
from uuid import uuid4

from backend.app.integrations.spending import (
    SpendingBudget,
    SpendingLimitError,
    current_spending_budget,
)
from backend.app.observability.progress import ProgressTracer, current_progress
from backend.app.observability.run_trace import NullRunTracer
from backend.app.policies.trip_dates import (
    DateProvider,
    SystemDateProvider,
    TripDatePolicyError,
)
from backend.app.schemas.interpreted_requirements import ClarificationRequired
from backend.app.schemas.planning import PlanningResult, SystemVersion
from backend.app.schemas.product import ProductPlanResult
from backend.app.schemas.request import PlanningRequest, TravelRequirements
from backend.app.services.planner_runtime import PlannerRuntime
from backend.app.services.preference_interpretation import validate_planning_request
from backend.app.services.product_evidence import ProductEvidenceCollector
from backend.app.services.product_introductions import ProductIntroductions
from backend.app.services.product_presentation import present_product


class PlanningNeedsClarificationError(RuntimeError):
    """Signal that the product request lacks requirements needed for planning."""

    def __init__(self, requirements: TravelRequirements, issues: dict | None = None) -> None:
        self.issues = issues or {}
        self.requirements = requirements
        super().__init__("The travel request needs clarification")


class PlanningFailedError(RuntimeError):
    """Hide active planner implementation details from the product API."""


class PlanningService:
    """Run the active planner behind a version-agnostic product boundary."""

    def __init__(
        self,
        runtime: PlannerRuntime,
        date_provider: DateProvider | None = None,
        *,
        introductions: ProductIntroductions | None = None,
        spend_limit_usd=None,
    ) -> None:
        self._runtime = runtime
        self._date_provider = date_provider or SystemDateProvider()
        self._introductions = introductions or ProductIntroductions()
        self._spend_limit_usd = spend_limit_usd

    def validate(
        self, request: PlanningRequest, *, reference_date: date | None = None
    ) -> PlanningRequest:
        return validate_planning_request(request, reference_date or self._date_provider.today())

    def reference_date(self) -> date:
        return self._date_provider.today()

    async def plan(
        self, request: PlanningRequest, *, reference_date: date | None = None,
    ) -> ProductPlanResult:
        if self._spend_limit_usd is None or current_spending_budget() is not None:
            return await self._plan(request, reference_date=reference_date)
        with SpendingBudget(self._spend_limit_usd).activate() as budget:
            result = await self._plan(request, reference_date=reference_date)
            if budget.blocked:
                raise PlanningFailedError("Generation spending allowance exhausted")
            return result

    async def _plan(
        self, request: PlanningRequest, *, reference_date: date | None = None
    ) -> ProductPlanResult:
        """Run V3, then decorate only the final Product presentation."""
        observer = current_progress()
        evidence = ProductEvidenceCollector(
            ProgressTracer(observer) if observer else NullRunTracer(uuid4())
        )
        try:
            result = await self._runtime.run(
                SystemVersion.V3,
                request,
                reference_date=reference_date or self._date_provider.today(),
                tracer=evidence,
            )
        except ClarificationRequired as exc:
            raise PlanningNeedsClarificationError(
                request.trip_requirements(), exc.as_dict()
            ) from exc
        except (TripDatePolicyError, TimeoutError):
            raise
        except Exception as exc:
            raise PlanningFailedError("The active planner failed") from exc
        descriptions = await self._introductions.generate(result.itinerary, evidence)
        budget = current_spending_budget()
        if budget is not None and budget.blocked:
            raise PlanningFailedError("Generation spending allowance exhausted") from (
                SpendingLimitError("generation_spending_limit: incomplete generation")
            )
        return present_product(result, evidence, descriptions)


class DeveloperPlanningService:
    """Run currently implemented research planners for local inspection."""

    def __init__(
        self,
        runtime: PlannerRuntime,
        date_provider: DateProvider | None = None,
    ) -> None:
        self._runtime = runtime
        self._date_provider = date_provider or SystemDateProvider()

    def reference_date(self, override: date | None = None) -> date:
        return override or self._date_provider.today()

    async def plan(
        self,
        version: SystemVersion,
        request: PlanningRequest,
        *,
        reference_date: date | None = None,
    ) -> PlanningResult:
        """Select a real research runner without narrowing its result model."""

        effective_reference_date = self.reference_date(reference_date)
        return await self._runtime.run(
            version,
            request,
            reference_date=effective_reference_date,
        )
