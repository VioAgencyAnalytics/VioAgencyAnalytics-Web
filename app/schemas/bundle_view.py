"""Presentation-only models. No business metric defaults or calculations."""
from dataclasses import dataclass, field
from typing import Any

Scalar = str | int | float | None


@dataclass
class QualityView:
    status: str = 'unknown'
    warnings: list[str] = field(default_factory=list)
    latest_date: str | None = None


@dataclass
class MetricView:
    key: str
    label: str
    value: Scalar = None
    unit: str = ''
    previous: Scalar = None
    delta: Scalar = None
    source: str = ''
    data_date: str | None = None
    available: bool = False
    source_key: str = ''


@dataclass
class ChartView:
    title: str
    kind: str
    labels: list[str]
    values: list[int | float | None]
    source: str
    unit: str = ''
    data_date: str | None = None
    status: str = 'available'


@dataclass
class TableView:
    title: str
    columns: list[dict[str, str]]
    rows: list[dict[str, Any]]
    source: str
    status: str = 'available'


@dataclass
class EvidenceCard:
    claim: str | None = None
    metric: str | None = None
    before: Scalar = None
    after: Scalar = None
    period: dict[str, str] | None = None
    source: str | None = None
    url: str | None = None
    data_date: str | None = None
    quality: QualityView = field(default_factory=QualityView)
    verification: str = 'unverified'
    asset_id: str | None = None
    evidence_id: str | None = None


@dataclass
class OpportunityCard:
    title: str | None = None
    reason: str | None = None
    supporting_data: list[str] = field(default_factory=list)
    priority: str | None = None
    action: str | None = None
    conditions: list[str] = field(default_factory=list)


@dataclass
class SourceView:
    name: str
    status: str
    latest_date: str | None
    fetched_at: str | None
    url: str | None
    warnings: list[str]
    error: str | None
    provenance: str


@dataclass
class SectionView:
    key: str
    dom_id: str
    label: str
    report_type: str | None
    period: dict[str, str]
    valid: bool | None
    state: str
    quality: QualityView
    dataset_id: str | None = None
    created_at: str | None = None
    provenance: str = 'unverified'
    metrics: list[MetricView] = field(default_factory=list)
    charts: list[ChartView] = field(default_factory=list)
    tables: list[TableView] = field(default_factory=list)
    sources: list[SourceView] = field(default_factory=list)
    evidence: list[EvidenceCard] = field(default_factory=list)
    opportunities: list[OpportunityCard] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    approval: dict[str, Any] = field(default_factory=dict)
    platforms: list[dict[str, str]] = field(default_factory=list)


@dataclass
class BundleView:
    report_id: str
    revision: int
    status: str
    name: str
    client_name: str
    period: dict[str, str]
    comparison: dict[str, str] | None
    generated_at: str | None
    published_at: str | None
    quality: QualityView
    sections: list[SectionView]
    default_section: str | None
    provenance: str = 'unverified'
    branding_name: str | None = None
