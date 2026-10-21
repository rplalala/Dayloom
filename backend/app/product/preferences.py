"""Supported Product preference domains shared by profile and editor snapshots."""

from typing import Literal

Interest = Literal[
    "City walks",
    "History & culture",
    "Art & museums",
    "Nature",
    "Local food",
    "Photography",
    "Family experiences",
    "Free exploration",
]
Currency = Literal[
    "AUD",
    "USD",
    "EUR",
    "GBP",
    "CNY",
    "JPY",
    "CAD",
    "NZD",
    "SGD",
    "HKD",
    "CHF",
    "KRW",
    "INR",
    "THB",
    "MYR",
    "IDR",
    "VND",
    "PHP",
    "AED",
    "ZAR",
]
Pace = Literal["relaxed", "balanced", "rich"]
Transport = Literal["walk", "transit", "drive"]
