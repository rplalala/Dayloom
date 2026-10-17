"""Shared offline identity command options for batch, V0 and controlled entry points."""

from .identity import resolve_identities, resolve_legacy_identities
from .identity_llm import prepare_identity_judgment, resolve_llm_identities
from .identity_program import resolve_versioned_identities


def add_identity_options(parser):
    parser.add_argument(
        "--common-subjects",
        action="store_true",
        help="Use common independent requirement targets and V0 visit-only judgments",
    )
    parser.add_argument(
        "--prepare-subjects",
        action="store_true",
        help="Prepare the common-subject packet offline; requires --common-subjects",
    )
    parser.add_argument("--subject-result", help="Saved common-subject model result")
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Print a V0 visit/requirement-target packet; send nothing",
    )
    parser.add_argument("--model", help="Explicit model name for packet preparation")
    parser.add_argument("--model-result", help="Saved source-bound model-result JSON")
    parser.add_argument(
        "--legacy", action="store_true", help="Explicit historical human/audit replay"
    )
    parser.add_argument("--reviews", help="Historical human review JSON; requires --legacy")
    parser.add_argument(
        "--historical-llm", action="store_true", help="Explicit historical all-version LLM replay"
    )
    parser.add_argument(
        "--historical-association",
        action="store_true",
        help="Explicit versioned_api_identity_2 replay without physical associations",
    )
    parser.add_argument(
        "--historical-program",
        action="store_true",
        help="Explicit versioned_api_identity_1 replay with shared programmatic targets",
    )


def identity_command(intake, evidence, args, read, *, audit=None, legacy=None):
    """Choose one explicit policy and reject contradictory command options."""
    if (args.prepare_subjects or args.subject_result) and not args.common_subjects:
        raise ValueError("Subject options require --common-subjects")
    if args.common_subjects:
        if (
            args.legacy
            or args.historical_llm
            or args.historical_program
            or args.historical_association
            or args.reviews
            or audit is not None
        ):
            raise ValueError("Common subjects cannot use historical identity policies")
        if args.prepare_subjects:
            if args.prepare or args.model_result or args.subject_result:
                raise ValueError("Subject preparation cannot import results or prepare visits")
            from .subject_correspondence import prepare_subject_judgment

            packet = prepare_subject_judgment(intake, evidence, model=args.model)
            return (
                packet.to_dict() if packet else {"status": "skipped", "reason": "no_named_subjects"}
            )
        if args.prepare:
            if args.model_result or args.subject_result:
                raise ValueError("Packet preparation cannot import results")
            packet = prepare_identity_judgment(intake, evidence, model=args.model, visits_only=True)
            return packet.to_dict() if packet else {"status": "skipped", "reason": "no_v0_visits"}
        if args.model:
            raise ValueError("--model requires packet preparation")
        return resolve_versioned_identities(
            intake,
            evidence,
            model_result=read(args.model_result),
            common_subjects=True,
            subject_result=read(args.subject_result),
        ).to_dict()
    if args.legacy:
        if (
            args.prepare
            or args.model
            or args.model_result
            or args.historical_llm
            or args.historical_program
            or args.historical_association
        ):
            raise ValueError("Legacy replay cannot use model options")
        if legacy is not None:
            return legacy(read(args.reviews)).to_dict()
        return resolve_legacy_identities(intake, evidence, read(args.reviews), audit).to_dict()
    if args.reviews or audit is not None:
        raise ValueError("Human/audit inputs require --legacy")
    if sum((args.historical_program, args.historical_llm, args.historical_association)) > 1:
        raise ValueError("Choose only one historical identity policy")
    if args.prepare:
        if args.model_result:
            raise ValueError("Packet preparation cannot import a model result")
        return prepare_identity_judgment(
            intake,
            evidence,
            model=args.model,
            historical=args.historical_llm,
            legacy_v0=args.historical_program,
        ).to_dict()
    if args.model:
        raise ValueError("--model requires --prepare; saved result binds its model")
    if args.historical_program or args.historical_association:
        return resolve_versioned_identities(
            intake,
            evidence,
            model_result=read(args.model_result),
            historical=args.historical_program,
            previous=args.historical_association,
        ).to_dict()
    resolver = resolve_llm_identities if args.historical_llm else resolve_identities
    return resolver(intake, evidence, model_result=read(args.model_result)).to_dict()
