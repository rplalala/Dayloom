"""Published transport envelope for the current Foundry GPT-6 Luna deployment.

Source: Microsoft Foundry models sold directly by Azure, GPT-6 capabilities.
These provider ceilings are separate from each runtime profile's operating budgets.
"""

FOUNDRY_LUNA_CONTEXT_TOKENS = 1_050_000
FOUNDRY_LUNA_MAX_INPUT_TOKENS = 922_000
FOUNDRY_LUNA_MAX_OUTPUT_TOKENS = 128_000

# The pinned official-search model has a separate, smaller output envelope.
OPENAI_SEARCH_MAX_OUTPUT_TOKENS = 32_768
