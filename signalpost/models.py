from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal,InvalidOperation
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

State = Literal["available", "not_available", "blocked", "not_applicable", "ambiguous", "failed"]


def utcnow() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def org_number(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"^(?:NO\s*)", "", text, flags=re.I)
    text = re.sub(r"\s*(?:MVA)$", "", text, flags=re.I)
    text = re.sub(r"[ .]", "", text)
    if not re.fullmatch(r"[0-9]{9}", text):
        raise ValueError("Organisation number requires nine ASCII digits")
    check = 11 - sum(int(a) * b for a, b in zip(text[:8], (3, 2, 7, 6, 5, 4, 3, 2))) % 11
    check = 0 if check == 11 else check
    if check == 10 or check != int(text[8]) or text == "000000000":
        raise ValueError("Organisation-number checksum failed")
    return text


class Evidence(BaseModel):
    id: str
    organisation_number: str
    source_url: str
    final_url: str
    source_class: str
    source_identifier: str
    retrieved_at: str
    source_published_at: str | None = None
    effective_at: str | None = None
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    storage_ref: str
    claim_span: str
    json_path: str | None = None
    extraction_method: str = "deterministic-v1"
    claim_bindings: dict[str, str] = Field(default_factory=dict)


class Claim(BaseModel):
    id: str
    field: str
    value: Any = None
    availability: State
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    effective_at: str | None = None
    reporting_period: dict[str, str] | None = None
    first_seen: str | None = None
    last_checked: str | None = None
    stale: bool = False
    retracted: bool = False

    @model_validator(mode="after")
    def supported(self):
        if self.retracted and (self.availability=='available' or not self.evidence_ids):
            raise ValueError('Retracted attribution must be unavailable with correction evidence')
        if self.availability == "available" and (self.value is None or not self.evidence_ids):
            raise ValueError("Published value requires evidence")
        if self.availability != "available" and self.value is not None:
            raise ValueError("Unavailable claim cannot contain a value")
        if self.field.startswith("financial.") and self.availability == "available":
            v = self.value
            if not isinstance(v, dict) or not {"amount", "currency", "scale", "scope", "organisation_number", "period"} <= v.keys():
                raise ValueError("Incomplete financial dimensions")
            if not v["currency"] or not v["period"] or v["scope"] not in {"company", "group"} or v["scale"] != 1:
                raise ValueError("Unverified financial scope, units or period")
            try:
                if not Decimal(str(v['amount'])).is_finite():raise ValueError('Non-finite financial amount')
            except InvalidOperation:
                raise ValueError('Invalid financial decimal amount') from None
        return self


class InputRow(BaseModel):
    organisation_number: str
    id: str | int | None = None
    input_id: str | int | None = None
    evaluation_split: str | None = None
    sample_slice: str | None = None


class Envelope(BaseModel):
    schema_version: str
    organisation_number: str
    input_id: Any = None
    run_id: str
    state: str
    availability: State
    started_at: str
    completed_at: str
    run: dict[str, Any]
    legal_identity: dict[str, Any]
    modules: dict[str, dict[str, Any]]
    claims: list[Claim]
    evidence: list[Evidence]
    source_snapshots: list[dict[str, Any]]
    profile: dict[str, Any]
    summary: dict[str, Any]
    website_candidates: list[dict[str, Any]]
    changes: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    refresh: dict[str, Any]
    operations: dict[str, Any]


MODULE_STATE = {"available": "complete", "not_available": "not_found", "blocked": "blocked_policy",
                "not_applicable": "not_applicable", "ambiguous": "not_found", "failed": "source_error"}


def validate_envelopes(rows: list[dict], inputs: list[dict] | None = None) -> dict:
    errors = []
    seen = set()
    if inputs is not None and len(rows) != len(inputs):
        errors.append("Envelope count differs from input count")
    for index, row in enumerate(rows):
        try:
            Envelope.model_validate(row)
            if row["organisation_number"] in seen:
                raise ValueError("Duplicate result")
            seen.add(row["organisation_number"])
            if inputs is not None and row["organisation_number"] != inputs[index]["organisation_number"]:
                raise ValueError("Input order/identifier mismatch")
            if row["availability"] not in MODULE_STATE or row["run"]["terminal_status"] != "completed":
                raise ValueError("Nonterminal result")
            for module in row['modules'].values():
                if module['availability'] not in MODULE_STATE or module['state'] != MODULE_STATE[module['availability']]:
                    raise ValueError('Module status is not a valid terminal mapping')
            for timestamp in (row['started_at'], row['completed_at'], *(e['retrieved_at'] for e in row['evidence'])):
                offset = datetime.fromisoformat(timestamp.replace('Z','+00:00')).utcoffset()
                if offset is None or offset.total_seconds() != 0:
                    raise ValueError('Evidence/run timestamps must be UTC')
            evidence = {e["id"]: Evidence.model_validate(e) for e in row["evidence"]}
            if len(evidence) != len(row["evidence"]):
                raise ValueError("Duplicate evidence identifier")
            for raw in row["claims"]:
                c = Claim.model_validate(raw)
                for eid in c.evidence_ids:
                    e = evidence[eid]
                    if e.organisation_number != row["organisation_number"]:
                        raise ValueError("Evidence belongs to another legal entity")
                if c.availability == "available" and not any(evidence[eid].claim_bindings.get(c.id) == digest(canonical(c.value).encode()) for eid in c.evidence_ids):
                    raise ValueError("Evidence-to-claim value binding missing or changed")
                if c.field.startswith("financial.") and c.availability == "available" and c.value["organisation_number"] != row["organisation_number"]:
                    raise ValueError("Financial company mismatch")
            current_description_ids={c['id'] for c in row['claims'] if c['availability']=='available' and not c['stale'] and c['field'] in {'registered_activity','website_description'}}
            if set(row['summary'].get('business_description_claim_ids',[]))-current_description_ids:
                raise ValueError('Summary references an unavailable, stale or unrelated description')
            for key in ("profile", "modules", "changes", "errors", "operations", "refresh", "source_snapshots"):
                if key not in row:
                    raise ValueError(f"Missing section {key}")
        except (KeyError, ValueError, TypeError, IndexError) as exc:
            errors.append(f"row {index}: {exc}")
    return {"passed": not errors, "count": len(rows), "errors": errors}
