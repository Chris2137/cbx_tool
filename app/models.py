from dataclasses import dataclass
from typing import Any
from decimal import Decimal, InvalidOperation

@dataclass
class CodeName:
    code: str | None
    name: str | None

@dataclass
class AQLInfo:
    critical_level: CodeName | None
    major_level: CodeName | None
    minor_level: CodeName | None
    inspection_level: CodeName | None
    inspection_procedure: CodeName | None
    is_allow_realtime_update: CodeName | None
    sampling_plan: CodeName | None
    sampling_method: CodeName | None
    lookup_list_name: str | None = None

@dataclass
class AQLResult:
    code_letter: str | None
    sample_size: Any
    acceptance_number: Any
    rejection_number: Any
    iteration: Any

def to_code_name(value: dict | None) -> CodeName | None:
    if not isinstance(value, dict):
        return None
    code = value.get("code")
    name = value.get("name")
    if not code and name:
        code = name
    return CodeName(code=code, name=name)

def to_decimal(value: Any) -> Decimal:
    if value is None:
        raise RuntimeError("Numeric value is missing")
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise RuntimeError(f"Invalid numeric value: {value}")