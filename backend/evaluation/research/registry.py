"""Lazy report registry: optional research tracks own their material readers."""

from importlib import import_module

TRACKS = {
    "population": "backend.evaluation.research.population",
    "opportunities": "backend.evaluation.research.opportunities",
    "relevance": "backend.evaluation.research.relevance",
    "repair": "backend.evaluation.research.repair",
    "tradeoffs": "backend.evaluation.research.tradeoffs",
}


def build_report(context, track):
    module = import_module(TRACKS[track])
    return getattr(module, track + "_report")(context), module.markdown
