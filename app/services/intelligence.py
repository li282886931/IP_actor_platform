from sqlalchemy.orm import Session

from app.datasets.market_dossier import MARKET_DOSSIER
from app.models import Assumption, Artist, DataSource, Evidence, ExternalDataJob, Fact, Project, Risk, Tenant, User
from app.services.auth import get_or_create_default_context


def connector_health(source: DataSource):
    if source.status == 'disabled':
        return False, 'Data source is disabled'
    if source.status != 'active':
        return False, 'Data source is not active'
    if not (source.credential_ref or '').strip():
        return False, 'Data source has no credential reference'
    return True, ''


def _truncate(value: str, length: int):
    text_value = str(value or '')
    return text_value if len(text_value) <= length else text_value[:length]


def _market_dossier_summary(row: dict):
    cells = row["cells"]
    return "；".join(
        f"{key}：{value}"
        for key, value in cells.items()
        if value not in (None, '')
    )


def _market_dossier_title(sheet: dict, row: dict):
    primary_header = sheet["headers"][0]
    primary = row["cells"].get(primary_header) or row["id"]
    return _truncate(f"{sheet['sheet']} - {primary}", 255)


def _market_dossier_source(row: dict):
    return _truncate(f"market-dossier:{row['id']}", 128)


def _upsert_market_dossier_evidence(db: Session, project: Project, sheet: dict, row: dict):
    file_url = f"market-dossier://zhao-yazhi/{row['id']}"
    evidence = db.query(Evidence).filter(
        Evidence.project_id == project.id,
        Evidence.file_url == file_url,
    ).first()
    if not evidence:
        evidence = Evidence(project_id=project.id, file_url=file_url)
        db.add(evidence)
    evidence.name = _market_dossier_title(sheet, row)
    evidence.evidence_type = 'market_dossier'
    evidence.source = _market_dossier_source(row)
    evidence.status = 'needs_review'
    evidence.meta = {
        "artist_name": "赵雅芝",
        "sheet": sheet["sheet"],
        "row_id": row["id"],
        "headers": sheet["headers"],
        "cells": row["cells"],
        "system_target": row["system_target"],
        "handling": row["handling"],
        "record_type": row["record_type"],
        "capture_plan": row["capture_plan"],
        "requires_human_verification": True,
    }
    return evidence


def _upsert_market_dossier_fact(db: Session, project: Project, sheet: dict, row: dict):
    source = _market_dossier_source(row)
    fact = db.query(Fact).filter(Fact.project_id == project.id, Fact.source == source).first()
    if not fact:
        fact = Fact(project_id=project.id, source=source)
        db.add(fact)
    fact.title = _market_dossier_title(sheet, row)
    fact.content = _market_dossier_summary(row)
    fact.status = 'pending'
    return fact


def _upsert_market_dossier_assumption(db: Session, project: Project, sheet: dict, row: dict):
    title = _market_dossier_title(sheet, row)
    assumption = db.query(Assumption).filter(
        Assumption.project_id == project.id,
        Assumption.title == title,
    ).first()
    if not assumption:
        assumption = Assumption(project_id=project.id, title=title)
        db.add(assumption)
    assumption.content = _market_dossier_summary(row)
    assumption.confidence = 70
    assumption.status = 'active'
    return assumption


def _upsert_market_dossier_risk(db: Session, project: Project, sheet: dict, row: dict):
    title = _market_dossier_title(sheet, row)
    risk = db.query(Risk).filter(Risk.project_id == project.id, Risk.title == title).first()
    if not risk:
        risk = Risk(project_id=project.id, title=title)
        db.add(risk)
    cells = row["cells"]
    risk.level = 'high' if any(keyword in _market_dossier_summary(row) for keyword in ['负面', '风险', '争议', '不可用']) else 'medium'
    risk.mitigation = cells.get('合作/对标建议') or cells.get('大秀可落地方案建议') or _market_dossier_summary(row)
    risk.status = 'open'
    return risk


def _upsert_market_dossier_external_job(db: Session, tenant: Tenant, user: User, project: Project, row: dict):
    plan = row["capture_plan"]
    job = db.query(ExternalDataJob).filter(
        ExternalDataJob.tenant_id == tenant.id,
        ExternalDataJob.project_id == project.id,
        ExternalDataJob.purpose == plan["purpose"],
        ExternalDataJob.query == plan["query"],
    ).first()
    if not job:
        job = ExternalDataJob(
            tenant_id=tenant.id,
            project_id=project.id,
            purpose=plan["purpose"],
            query=plan["query"],
            requested_by=user.id,
        )
        db.add(job)
    job.source_type = plan["source_type"]
    job.provider = plan["provider"]
    job.status = job.status or 'queued'
    job.parameters = {
        "artist_name": "赵雅芝",
        "dossier_row_id": row["id"],
        "system_target": row["system_target"],
        "requires_human_verification": True,
    }
    job.result = job.result or {}
    return job


def seed_market_dossier_data(db: Session):
    tenant, user = get_or_create_default_context(db)
    row_count = sum(len(sheet["rows"]) for sheet in MARKET_DOSSIER)

    artist = db.query(Artist).filter(Artist.name == "赵雅芝").first()
    if not artist:
        artist = Artist(name="赵雅芝")
        db.add(artist)
    artist.tags = "港星黄金时代/白素贞/东方赫本/冻龄女神/国风高定"
    artist.heat_score = 86
    artist.fan_count = "多平台待核验"
    artist.risk_level = 1
    artist.profile = {
        **(artist.profile or {}),
        "market_positioning": "经典影视 IP 与东方女性美学结合的大秀型艺人",
        "market_dossier": {
            "source": "赵雅芝市场分析 Excel 资料包",
            "sheet_count": len(MARKET_DOSSIER),
            "row_count": row_count,
            "sheets": MARKET_DOSSIER,
            "requires_human_verification": True,
        },
    }

    project = db.query(Project).filter(
        Project.tenant_id == tenant.id,
        Project.name == "赵雅芝大秀市场分析",
    ).first()
    if not project:
        project = Project(
            tenant_id=tenant.id,
            name="赵雅芝大秀市场分析",
            type='concert',
            created_by=user.id,
        )
        db.add(project)
        db.flush()
    project.artist_name = "赵雅芝"
    project.city = project.city or "待定"
    project.venue = project.venue or "待定"
    project.schedule = project.schedule or "待定"
    project.status = project.status or 'draft'

    for sheet in MARKET_DOSSIER:
        for row in sheet["rows"]:
            _upsert_market_dossier_evidence(db, project, sheet, row)
            if row["record_type"] == 'fact':
                _upsert_market_dossier_fact(db, project, sheet, row)
            elif row["record_type"] == 'assumption':
                _upsert_market_dossier_assumption(db, project, sheet, row)
            elif row["record_type"] == 'risk':
                _upsert_market_dossier_risk(db, project, sheet, row)
            if row["handling"] == 'external_capture':
                _upsert_market_dossier_external_job(db, tenant, user, project, row)

    db.commit()
