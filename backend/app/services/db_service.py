from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings

logger = logging.getLogger(__name__)


def _strip_json_null_bytes(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_strip_json_null_bytes(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_json_null_bytes(item) for item in value]
    if isinstance(value, dict):
        return {
            _strip_json_null_bytes(key) if isinstance(key, str) else key: _strip_json_null_bytes(item)
            for key, item in value.items()
        }
    return value


class CompanyProfileDatabase:
    def __init__(self) -> None:
        self._ready = False

    @property
    def enabled(self) -> bool:
        return bool(settings.database_url.strip())

    def _verify_connection(self) -> None:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

    def _ensure_schema_sync(self) -> None:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                # Set Schema search path
                cur.execute("CREATE SCHEMA IF NOT EXISTS npip;")
                cur.execute("SET search_path TO npip, public;")
                cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
                
                # 1. Create Framework & User tables
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id UUID PRIMARY KEY,
                        user_principal_name VARCHAR(255) UNIQUE NOT NULL,
                        display_name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS roles (
                        role_id UUID PRIMARY KEY,
                        role_code VARCHAR(100) UNIQUE NOT NULL,
                        role_name VARCHAR(150) NOT NULL,
                        description TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_roles (
                        user_role_id UUID PRIMARY KEY,
                        user_id UUID NOT NULL REFERENCES users(user_id),
                        role_id UUID NOT NULL REFERENCES roles(role_id),
                        valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        valid_to TIMESTAMPTZ,
                        assigned_by UUID REFERENCES users(user_id),
                        assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(user_id, role_id, valid_from)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS evaluation_frameworks (
                        framework_id UUID PRIMARY KEY,
                        framework_code VARCHAR(100) NOT NULL,
                        framework_name VARCHAR(255) NOT NULL,
                        version_no VARCHAR(50) NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
                        description TEXT,
                        created_by UUID REFERENCES users(user_id),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_by UUID REFERENCES users(user_id),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(framework_code, version_no)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS framework_gates (
                        framework_gate_id UUID PRIMARY KEY,
                        framework_id UUID NOT NULL REFERENCES evaluation_frameworks(framework_id),
                        gate_code VARCHAR(50) NOT NULL,
                        gate_group VARCHAR(100) NOT NULL,
                        description TEXT NOT NULL,
                        evaluation_check TEXT,
                        rule_logic TEXT,
                        decision_rule TEXT,
                        active_flag BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(framework_id, gate_code)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS framework_score_criteria (
                        framework_score_criterion_id UUID PRIMARY KEY,
                        framework_id UUID NOT NULL REFERENCES evaluation_frameworks(framework_id),
                        pillar_code VARCHAR(50) NOT NULL,
                        pillar_name VARCHAR(150) NOT NULL,
                        criterion_code VARCHAR(100) NOT NULL,
                        criterion_name TEXT NOT NULL,
                        score_min INT NOT NULL DEFAULT 0,
                        score_max INT NOT NULL DEFAULT 5,
                        pillar_weight_pct NUMERIC(5,2) NOT NULL,
                        significance_level VARCHAR(50) NOT NULL,
                        significance_rationale TEXT,
                        scoring_guidance_json JSONB,
                        active_flag BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(framework_id, criterion_code)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS framework_red_flags (
                        framework_red_flag_id UUID PRIMARY KEY,
                        framework_id UUID NOT NULL REFERENCES evaluation_frameworks(framework_id),
                        red_flag_code VARCHAR(50) NOT NULL,
                        flag_group VARCHAR(150) NOT NULL,
                        description TEXT NOT NULL,
                        interpretation VARCHAR(100),
                        severity_level VARCHAR(50),
                        active_flag BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(framework_id, red_flag_code)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS framework_decision_rules (
                        framework_decision_rule_id UUID PRIMARY KEY,
                        framework_id UUID NOT NULL REFERENCES evaluation_frameworks(framework_id),
                        min_score_pct NUMERIC(5,2) NOT NULL,
                        max_score_pct NUMERIC(5,2) NOT NULL,
                        recommendation_code VARCHAR(50) NOT NULL,
                        override_condition TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                
                # 2. Create Partner / Research tables
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS partners (
                        partner_id UUID PRIMARY KEY,
                        company_name VARCHAR(255) NOT NULL,
                        website_url TEXT,
                        headquarters_country VARCHAR(100),
                        headquarters_region VARCHAR(100),
                        founded_year INT,
                        employee_count INT,
                        funding_total_usd NUMERIC(18,2),
                        funding_stage VARCHAR(100),
                        summary TEXT,
                        industry_tags JSONB,
                        capability_tags JSONB,
                        technology_tags JSONB,
                        geography_tags JSONB,
                        competitor_tags JSONB,
                        source_profile_status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
                        latest_refresh_ts TIMESTAMPTZ,
                        created_by UUID REFERENCES users(user_id),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_by UUID REFERENCES users(user_id),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(company_name)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS partner_research_runs (
                        research_run_id UUID PRIMARY KEY,
                        partner_id UUID NOT NULL REFERENCES partners(partner_id),
                        research_version_no INT NOT NULL,
                        triggered_by_user_id UUID REFERENCES users(user_id),
                        trigger_type VARCHAR(50) NOT NULL,
                        research_status VARCHAR(50) NOT NULL,
                        extracted_profile_json JSONB NOT NULL,
                        evidence_summary_json JSONB,
                        source_references_json JSONB,
                        overall_confidence_score NUMERIC(5,2),
                        editable_override_flag BOOLEAN NOT NULL DEFAULT FALSE,
                        reviewed_by_user_id UUID REFERENCES users(user_id),
                        reviewed_at TIMESTAMPTZ,
                        snapshot_hash VARCHAR(128),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(partner_id, research_version_no)
                    );
                    """
                )
                
                # 3. Create Evaluation tables
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS partner_evaluations (
                        evaluation_id UUID PRIMARY KEY,
                        partner_id UUID NOT NULL REFERENCES partners(partner_id),
                        research_run_id UUID REFERENCES partner_research_runs(research_run_id),
                        framework_id UUID NOT NULL REFERENCES evaluation_frameworks(framework_id),
                        evaluation_version_no INT NOT NULL,
                        evaluation_context_json JSONB,
                        gate_overall_status VARCHAR(50),
                        total_score_pct NUMERIC(5,2),
                        recommendation_code VARCHAR(50),
                        decision_rationale TEXT,
                        overall_confidence_score NUMERIC(5,2),
                        pillar_scores_json JSONB,
                        evaluation_status VARCHAR(50) NOT NULL,
                        created_by UUID REFERENCES users(user_id),
                        created_by_role_id UUID REFERENCES roles(role_id),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        reviewed_by UUID REFERENCES users(user_id),
                        reviewed_at TIMESTAMPTZ,
                        approved_by UUID REFERENCES users(user_id),
                        approved_at TIMESTAMPTZ,
                        updated_by UUID REFERENCES users(user_id),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(partner_id, framework_id, evaluation_version_no)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS evaluation_gate_results (
                        evaluation_gate_result_id UUID PRIMARY KEY,
                        evaluation_id UUID NOT NULL REFERENCES partner_evaluations(evaluation_id),
                        gate_code VARCHAR(50) NOT NULL,
                        gate_group VARCHAR(100) NOT NULL,
                        gate_input_value JSONB,
                        gate_result VARCHAR(50) NOT NULL,
                        llm_commentary TEXT,
                        evidence_json JSONB,
                        confidence_score NUMERIC(5,2),
                        overridden_flag BOOLEAN NOT NULL DEFAULT FALSE,
                        override_reason TEXT,
                        overridden_by UUID REFERENCES users(user_id),
                        overridden_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(evaluation_id, gate_code)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS evaluation_criterion_scores (
                        evaluation_criterion_score_id UUID PRIMARY KEY,
                        evaluation_id UUID NOT NULL REFERENCES partner_evaluations(evaluation_id),
                        pillar_code VARCHAR(50) NOT NULL,
                        criterion_code VARCHAR(100) NOT NULL,
                        criterion_name TEXT NOT NULL,
                        assigned_score NUMERIC(5,2) NOT NULL,
                        pillar_weight_pct NUMERIC(5,2) NOT NULL,
                        significance_level VARCHAR(50) NOT NULL,
                        rationale_text TEXT,
                        evidence_json JSONB,
                        confidence_score NUMERIC(5,2),
                        criticality_flag VARCHAR(50),
                        weighted_contribution NUMERIC(8,4),
                        calculated_by UUID REFERENCES users(user_id),
                        calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        overridden_flag BOOLEAN NOT NULL DEFAULT FALSE,
                        override_reason TEXT,
                        overridden_by UUID REFERENCES users(user_id),
                        overridden_at TIMESTAMPTZ,
                        UNIQUE(evaluation_id, criterion_code)
                    );
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE evaluation_criterion_scores
                    ALTER COLUMN pillar_code TYPE VARCHAR(50),
                    ALTER COLUMN criterion_code TYPE VARCHAR(100),
                    ALTER COLUMN significance_level TYPE VARCHAR(50);
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS evaluation_red_flags (
                        evaluation_red_flag_id UUID PRIMARY KEY,
                        evaluation_id UUID NOT NULL REFERENCES partner_evaluations(evaluation_id),
                        red_flag_code VARCHAR(50) NOT NULL,
                        severity_level VARCHAR(50) NOT NULL,
                        detected_flag BOOLEAN NOT NULL DEFAULT TRUE,
                        rationale_text TEXT,
                        evidence_json JSONB,
                        overridden_flag BOOLEAN NOT NULL DEFAULT FALSE,
                        override_reason TEXT,
                        overridden_by UUID REFERENCES users(user_id),
                        overridden_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(evaluation_id, red_flag_code)
                    );
                    """
                )
                
                # 4. Create System Seed rows to satisfy foreign keys
                cur.execute(
                    """
                    INSERT INTO users (user_id, user_principal_name, display_name, email, is_active)
                    VALUES ('00000000-0000-0000-0000-000000000000', 'system_user', 'System User', 'system@npi.local', true)
                    ON CONFLICT (user_id) DO NOTHING;
                    """
                )
                cur.execute(
                    """
                    INSERT INTO roles (role_id, role_code, role_name, description)
                    VALUES ('00000000-0000-0000-0000-000000000001', 'SYSTEM_ADMIN', 'System Administrator', 'System Administrator Role')
                    ON CONFLICT (role_id) DO NOTHING;
                    """
                )
                cur.execute(
                    """
                    INSERT INTO user_roles (user_role_id, user_id, role_id)
                    VALUES ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000000', '00000000-0000-0000-0000-000000000001')
                    ON CONFLICT (user_role_id) DO NOTHING;
                    """
                )
                cur.execute(
                    """
                    INSERT INTO evaluation_frameworks (framework_id, framework_code, framework_name, version_no, status, description, created_by, updated_by)
                    VALUES ('00000000-0000-0000-0000-000000000003', 'DEFAULT', 'Default Evaluation Framework', '1.0', 'ACTIVE', 'System default evaluation framework', '00000000-0000-0000-0000-000000000000', '00000000-0000-0000-0000-000000000000')
                    ON CONFLICT (framework_id) DO NOTHING;
                    """
                )
                
                conn.commit()

    async def connect(self) -> None:
        if not self.enabled:
            logger.warning("Database integration is disabled; DATABASE_URL is empty")
            return
        await asyncio.to_thread(self._verify_connection)
        await asyncio.to_thread(self._ensure_schema_sync)
        self._ready = True
        logger.info("Database connection verified")

    async def disconnect(self) -> None:
        self._ready = False

    def _require_ready(self) -> None:
        if not self.enabled:
            raise RuntimeError("Database integration is disabled. Set DATABASE_URL to enable it.")
        if not self._ready:
            raise RuntimeError("Database is not ready.")

    def _save_company_profile_sync(self, *, company_name: str, artefact: dict[str, Any], username: str) -> str:
        logger.info("Database: Saving company profile for company_name=%s (username=%s)", company_name, username)
        safe_company_name = company_name.replace("\x00", "")
        safe_artefact = _strip_json_null_bytes(artefact)
        data = safe_artefact.get("data") or {}
        
        website_url = data.get("website") or ""
        headquarters = data.get("headquarters") or ""
        headquarters_country = ""
        headquarters_region = ""
        if headquarters:
            parts = [p.strip() for p in headquarters.split(",")]
            if len(parts) >= 1:
                headquarters_country = parts[-1]
            if len(parts) >= 2:
                headquarters_region = parts[-2]
                
        founded_year = data.get("founded_year") or 0
        summary = safe_artefact.get("company_summary") or ""
        
        # Robust extraction of funding_total_usd and funding_stage
        funding_total_usd = 0
        funding_stage = ""
        enterprise = data.get("enterprise_credibility") or {}
        recent_rounds = []
        if "sub_parts" in enterprise:
            funding_facts = enterprise.get("sub_parts", {}).get("institutional_funding", {}).get("facts", {})
            funding_total_usd = funding_facts.get("total_funding_usd") or 0
            recent_rounds = funding_facts.get("recent_rounds") or []
        elif "funding" in enterprise:
            funding_facts = enterprise.get("funding") or {}
            funding_total_usd = funding_facts.get("total_funding_usd") or 0
            recent_rounds = funding_facts.get("recent_rounds") or []
            
        try:
            funding_total_usd = int(funding_total_usd)
        except Exception:
            funding_total_usd = 0
            
        if recent_rounds and isinstance(recent_rounds, list) and len(recent_rounds) > 0:
            first_round = recent_rounds[0]
            if isinstance(first_round, dict):
                funding_stage = first_round.get("round_type") or ""
            elif isinstance(first_round, str):
                funding_stage = first_round
                
        # Robust extraction of employee_count
        employee_count = None
        if "employee_count" in data:
            employee_count = data.get("employee_count")
        elif "employees" in data:
            employee_count = data.get("employees")
        elif "employee" in data:
            employee_count = data.get("employee")
        else:
            product_maturity = enterprise.get("sub_parts", {}).get("production_grade_product_evidence", {}).get("facts", {})
            if "employee_count" in product_maturity:
                employee_count = product_maturity.get("employee_count")
            elif "employees" in product_maturity:
                employee_count = product_maturity.get("employees")
                
        if employee_count is not None:
            try:
                employee_count = int(employee_count)
            except Exception:
                employee_count = None
                
        # Extract tags
        strategic = data.get("strategic_relevance") or {}
        strategic_parts = strategic.get("sub_parts") or {}
        
        # Industry vertical tags
        industry_ai = strategic_parts.get("industry_ai_alignment") or {}
        industry_tags = industry_ai.get("facts", {}).get("verticals") or []
        if not isinstance(industry_tags, list):
            industry_tags = [industry_tags] if industry_tags else []
            
        # Capability tags
        data_mod = strategic_parts.get("data_modernization_alignment") or {}
        ai_ops = strategic_parts.get("ai_operations_alignment") or {}
        capabilities = (
            (data_mod.get("facts", {}).get("capabilities") or []) + 
            (ai_ops.get("facts", {}).get("capabilities") or [])
        )
        capability_tags = list(dict.fromkeys([str(x) for x in capabilities if x]))
        
        # Technology tags
        delivery = data.get("delivery_feasibility") or {}
        delivery_parts = delivery.get("delivery_feasibility") or {}
        integration = delivery_parts.get("integration_feasibility") or {}
        techs = (
            (data_mod.get("facts", {}).get("platforms") or []) +
            (strategic_parts.get("conversational_ai_alignment", {}).get("facts", {}).get("interfaces") or []) +
            (integration.get("facts", {}).get("integration_requirements") or [])
        )
        technology_tags = list(dict.fromkeys([str(x) for x in techs if x]))
        
        # Geography tags
        geography_tags = []
        if headquarters_region:
            geography_tags.append(headquarters_region)
        if headquarters_country:
            geography_tags.append(headquarters_country)
            
        competitor_tags = []
            
        sys_user_id = '00000000-0000-0000-0000-000000000000'
        
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO npip, public;")
                
                # Check if partner already exists or create new
                logger.info("Database: Checking if partner exists for company: %s", safe_company_name)
                cur.execute(
                    """
                    SELECT partner_id FROM partners WHERE company_name = %s;
                    """,
                    (safe_company_name,)
                )
                row = cur.fetchone()
                if row:
                    partner_id = row[0]
                    # Update partner record
                    logger.info("Database: Partner exists (partner_id=%s). Updating partner info.", partner_id)
                    logger.info(
                        "Database: Partner update values - website_url=%r, headquarters_country=%r, headquarters_region=%r, founded_year=%r, employee_count=%r, funding_total_usd=%r, funding_stage=%r, summary=%r, industry_tags=%r, capability_tags=%r, technology_tags=%r, geography_tags=%r, competitor_tags=%r",
                        website_url, headquarters_country, headquarters_region, founded_year, employee_count, funding_total_usd, funding_stage, summary, industry_tags, capability_tags, technology_tags, geography_tags, competitor_tags
                    )
                    cur.execute(
                        """
                        UPDATE partners
                        SET website_url = %s, headquarters_country = %s, headquarters_region = %s, founded_year = %s, employee_count = %s, funding_total_usd = %s, funding_stage = %s, summary = %s, industry_tags = %s, capability_tags = %s, technology_tags = %s, geography_tags = %s, competitor_tags = %s, updated_at = NOW()
                        WHERE partner_id = %s;
                        """,
                        (
                            website_url, headquarters_country, headquarters_region, founded_year, employee_count, funding_total_usd, funding_stage, summary,
                            psycopg.types.json.Jsonb(industry_tags),
                            psycopg.types.json.Jsonb(capability_tags),
                            psycopg.types.json.Jsonb(technology_tags),
                            psycopg.types.json.Jsonb(geography_tags),
                            psycopg.types.json.Jsonb(competitor_tags),
                            partner_id
                        )
                    )
                else:
                    partner_id = str(uuid.uuid4())
                    logger.info("Database: Partner does not exist. Inserting new partner record (partner_id=%s)", partner_id)
                    logger.info(
                        "Database: Partner insert values - company_name=%r, website_url=%r, headquarters_country=%r, headquarters_region=%r, founded_year=%r, employee_count=%r, funding_total_usd=%r, funding_stage=%r, summary=%r, industry_tags=%r, capability_tags=%r, technology_tags=%r, geography_tags=%r, competitor_tags=%r",
                        safe_company_name, website_url, headquarters_country, headquarters_region, founded_year, employee_count, funding_total_usd, funding_stage, summary, industry_tags, capability_tags, technology_tags, geography_tags, competitor_tags
                    )
                    cur.execute(
                        """
                        INSERT INTO partners (
                            partner_id, company_name, website_url, headquarters_country, headquarters_region, founded_year, employee_count, funding_total_usd, funding_stage, summary,
                            industry_tags, capability_tags, technology_tags, geography_tags, competitor_tags, created_by, updated_by
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            partner_id, safe_company_name, website_url, headquarters_country, headquarters_region, founded_year, employee_count, funding_total_usd, funding_stage, summary,
                            psycopg.types.json.Jsonb(industry_tags),
                            psycopg.types.json.Jsonb(capability_tags),
                            psycopg.types.json.Jsonb(technology_tags),
                            psycopg.types.json.Jsonb(geography_tags),
                            psycopg.types.json.Jsonb(competitor_tags),
                            sys_user_id, sys_user_id
                        )
                    )
                
                # Compute next research run version
                cur.execute(
                    """
                    SELECT COALESCE(MAX(research_version_no), 0) + 1 FROM partner_research_runs WHERE partner_id = %s;
                    """,
                    (partner_id,)
                )
                version_no = cur.fetchone()[0]
                
                # Insert research run
                research_run_id = str(uuid.uuid4())
                evidence = data.get("evidence") or {}
                evidence_sources = evidence.get("sources") or []
                
                logger.info(
                    "Database: Inserting research run (research_run_id=%s, version=%s) for partner_id=%s",
                    research_run_id, version_no, partner_id
                )
                logger.info("Database: Research run extracted profile JSON payload: %s", safe_artefact)
                logger.info("Database: Research run evidence JSON payload: %s", evidence)
                logger.info("Database: Research run sources JSON payload: %s", evidence_sources)
                cur.execute(
                    """
                    INSERT INTO partner_research_runs (
                        research_run_id, partner_id, research_version_no, triggered_by_user_id, trigger_type, research_status,
                        extracted_profile_json, evidence_summary_json, source_references_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        research_run_id,
                        partner_id,
                        version_no,
                        sys_user_id,
                        'MANUAL',
                        'COMPLETED',
                        psycopg.types.json.Jsonb(safe_artefact),
                        psycopg.types.json.Jsonb(evidence),
                        psycopg.types.json.Jsonb(evidence_sources)
                    )
                )
                conn.commit()
                logger.info("Database: Transaction committed. Saved company profile. research_run_id=%s", research_run_id)
                
        return research_run_id

    async def save_company_profile(self, *, company_name: str, artefact: dict[str, Any], username: str = "") -> str:
        self._require_ready()
        return await asyncio.to_thread(
            self._save_company_profile_sync,
            company_name=company_name,
            artefact=artefact,
            username=username,
        )

    def _list_company_profiles_sync(self, search: str = "", limit: int = 5) -> list[dict[str, Any]]:
        logger.info("Database: Fetching company profile list search=%r limit=%d", search, limit)
        search_term = search.strip()
        like_pattern = f"%{search_term}%"
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO npip, public;")
                if search_term:
                    logger.info("Database: Querying partners matching search pattern %r", like_pattern)
                    cur.execute(
                        """
                        SELECT r.research_run_id as id, p.company_name, '' as username, r.created_at
                        FROM partner_research_runs r
                        JOIN partners p ON r.partner_id = p.partner_id
                        WHERE p.company_name ILIKE %s
                           OR p.website_url ILIKE %s
                        ORDER BY r.created_at DESC
                        LIMIT %s;
                        """,
                        (like_pattern, like_pattern, limit),
                    )
                else:
                    logger.info("Database: Querying recent partners (limit=%d)", limit)
                    cur.execute(
                        """
                        SELECT r.research_run_id as id, p.company_name, '' as username, r.created_at
                        FROM partner_research_runs r
                        JOIN partners p ON r.partner_id = p.partner_id
                        ORDER BY r.created_at DESC
                        LIMIT %s;
                        """,
                        (limit,),
                    )
                rows = cur.fetchall()
                logger.info("Database: Successfully fetched %d profile(s) from database", len(rows))
        return [{**dict(row), "id": str(row["id"])} for row in rows]

    async def list_company_profiles(self, search: str = "", limit: int = 5) -> list[dict[str, Any]]:
        self._require_ready()
        return await asyncio.to_thread(self._list_company_profiles_sync, search, limit)

    def _get_company_profile_sync(self, profile_id: str | int) -> dict[str, Any] | None:
        logger.info("Database: Fetching company profile by profile_id=%s", profile_id)
        is_valid_uuid = False
        try:
            uuid.UUID(str(profile_id))
            is_valid_uuid = True
        except ValueError:
            pass
            
        if not is_valid_uuid:
            logger.warning("Database: Invalid UUID profile_id=%s format", profile_id)
            return None
            
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO npip, public;")
                cur.execute(
                    """
                    SELECT r.research_run_id as id, p.company_name, '' as username, r.extracted_profile_json as artefact, r.created_at
                    FROM partner_research_runs r
                    JOIN partners p ON r.partner_id = p.partner_id
                    WHERE r.research_run_id = %s;
                    """,
                    (str(profile_id),),
                )
                row = cur.fetchone()
        if not row:
            logger.info("Database: Company profile profile_id=%s not found", profile_id)
            return None
            
        res = dict(row)
        res["id"] = str(res["id"])
        logger.info("Database: Successfully fetched company profile for %s (id=%s)", res.get("company_name"), profile_id)
        return res

    async def get_company_profile(self, profile_id: str | int) -> dict[str, Any] | None:
        self._require_ready()
        return await asyncio.to_thread(self._get_company_profile_sync, profile_id)

    def _save_evaluation_report_sync(
        self,
        *,
        profile_id: str | int,
        evaluation_type: str,
        report_json: dict[str, Any],
    ) -> str:
        logger.info(
            "Database: Saving evaluation report for profile_id=%s (evaluation_type=%s)",
            profile_id,
            evaluation_type,
        )
        is_valid_uuid = False
        try:
            uuid.UUID(str(profile_id))
            is_valid_uuid = True
        except ValueError:
            pass
            
        if not is_valid_uuid:
            logger.warning("Database: Invalid research run UUID: %s", profile_id)
            raise ValueError(f"Invalid research run UUID: {profile_id}")
            
        safe_report_json = _strip_json_null_bytes(report_json)
        sys_user_id = '00000000-0000-0000-0000-000000000000'
        sys_role_id = '00000000-0000-0000-0000-000000000001'
        default_framework_id = '00000000-0000-0000-0000-000000000003'
        
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO npip, public;")
                
                # Fetch partner_id
                logger.info("Database: Fetching partner_id associated with research_run_id=%s", profile_id)
                cur.execute(
                    """
                    SELECT partner_id FROM partner_research_runs WHERE research_run_id = %s;
                    """,
                    (str(profile_id),)
                )
                row = cur.fetchone()
                if not row:
                    logger.error("Database: No research run found for UUID: %s", profile_id)
                    raise RuntimeError(f"No research run found for UUID: {profile_id}")
                partner_id = row[0]
                logger.info("Database: Found partner_id=%s for research_run_id=%s", partner_id, profile_id)
                
                # Compute version
                cur.execute(
                    """
                    SELECT COALESCE(MAX(evaluation_version_no), 0) + 1 
                    FROM partner_evaluations 
                    WHERE partner_id = %s AND framework_id = %s;
                    """,
                    (partner_id, default_framework_id)
                )
                eval_version_no = cur.fetchone()[0]
                
                evaluation_id = str(uuid.uuid4())
                
                gate_overall_status = None
                total_score_pct = None
                recommendation_code = None
                decision_rationale = None
                pillar_scores_json = None
                
                if evaluation_type == 'decision_intelligence':
                    priority = safe_report_json.get("overall_partnership_recommendation", {}).get("priority") or "LOW_PRIORITY"
                    reason = safe_report_json.get("overall_partnership_recommendation", {}).get("reason") or ""
                    
                    gate_statuses = []
                    for g_key in ('gate_1', 'gate_2', 'gate_3', 'gate_4', 'gate_5'):
                        g_data = safe_report_json.get(g_key)
                        if isinstance(g_data, dict) and g_data.get("status"):
                            gate_statuses.append(str(g_data.get("status")).upper())
                    
                    if 'FAIL' in gate_statuses:
                        gate_overall_status = 'FAIL'
                    elif 'DEFER' in gate_statuses or 'REVIEW' in gate_statuses:
                        gate_overall_status = 'DEFER'
                    else:
                        gate_overall_status = 'PASS'
                        
                    recommendation_code = priority
                    decision_rationale = reason
                    
                elif evaluation_type == 'scoring':
                    total_score_pct = safe_report_json.get("total_weighted_score") or 0.0
                    decision_rationale = safe_report_json.get("overall_summary") or ""
                    pillar_scores_json = safe_report_json.get("pillars") or {}
                
                # Insert main evaluations
                logger.info(
                    "Database: Inserting partner_evaluation (evaluation_id=%s, version=%s) for partner_id=%s",
                    evaluation_id, eval_version_no, partner_id
                )
                logger.info(
                    "Database: Evaluation data insert values - partner_id=%r, research_run_id=%r, framework_id=%r, evaluation_version_no=%r, gate_overall_status=%r, total_score_pct=%r, recommendation_code=%r, decision_rationale=%r, context_json=%s",
                    partner_id, str(profile_id), default_framework_id, eval_version_no, gate_overall_status, total_score_pct, recommendation_code, decision_rationale, safe_report_json
                )
                cur.execute(
                    """
                    INSERT INTO partner_evaluations (
                        evaluation_id, partner_id, research_run_id, framework_id, evaluation_version_no,
                        evaluation_context_json, gate_overall_status, total_score_pct, recommendation_code,
                        decision_rationale, evaluation_status, created_by, created_by_role_id, updated_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        evaluation_id,
                        partner_id,
                        str(profile_id),
                        default_framework_id,
                        eval_version_no,
                        psycopg.types.json.Jsonb(safe_report_json),
                        gate_overall_status,
                        total_score_pct,
                        recommendation_code,
                        decision_rationale,
                        'COMPLETED',
                        sys_user_id,
                        sys_role_id,
                        sys_user_id
                    )
                )
                
                # Insert sub-tables details
                if evaluation_type == 'decision_intelligence':
                    gate_groups = {
                        "gate_1": "Enterprise Credibility",
                        "gate_2": "Strategic Relevance",
                        "gate_3": "Delivery Feasibility",
                        "gate_4": "Commercial Viability",
                        "gate_5": "Compliance & Geo Risk"
                    }
                    for g_key, g_group in gate_groups.items():
                        g_data = safe_report_json.get(g_key)
                        if not isinstance(g_data, dict):
                            continue
                        
                        gate_code = g_key.upper()
                        gate_result = str(g_data.get("status") or "FAIL").upper()
                        llm_commentary = g_data.get("summary") or ""
                        gate_input_value = g_data.get("criteria") or {}
                        
                        logger.info("Database: Inserting evaluation_gate_result for gate %s (result=%s)", gate_code, gate_result)
                        logger.info(
                            "Database: Evaluation gate result insert values - gate_code=%r, gate_group=%r, gate_result=%r, llm_commentary=%r, gate_input_value=%s",
                            gate_code, g_group, gate_result, llm_commentary, gate_input_value
                        )
                        cur.execute(
                            """
                            INSERT INTO evaluation_gate_results (
                                evaluation_gate_result_id, evaluation_id, gate_code, gate_group,
                                gate_input_value, gate_result, llm_commentary
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s);
                            """,
                            (
                                str(uuid.uuid4()),
                                evaluation_id,
                                gate_code,
                                g_group,
                                psycopg.types.json.Jsonb(gate_input_value),
                                gate_result,
                                llm_commentary
                            )
                        )
                        
                        if g_key == "gate_5":
                            for flag_code, flag_val in gate_input_value.items():
                                if isinstance(flag_val, dict) and flag_val.get("decision") == "YES":
                                    logger.info("Database: Inserting evaluation_red_flag code=%s for evaluation_id=%s", flag_code.upper(), evaluation_id)
                                    logger.info(
                                        "Database: Evaluation red flag insert values - red_flag_code=%r, severity_level=%r, rationale_text=%r",
                                        flag_code.upper(), 'HIGH', flag_val.get("reason")
                                    )
                                    cur.execute(
                                        """
                                        INSERT INTO evaluation_red_flags (
                                            evaluation_red_flag_id, evaluation_id, red_flag_code,
                                            severity_level, detected_flag, rationale_text
                                        )
                                        VALUES (%s, %s, %s, %s, %s, %s);
                                        """,
                                        (
                                            str(uuid.uuid4()),
                                            evaluation_id,
                                            flag_code.upper(),
                                            'HIGH',
                                            True,
                                            flag_val.get("reason") or ""
                                        )
                                    )
                                    
                elif evaluation_type == 'scoring':
                    pillars = safe_report_json.get("pillars") or {}
                    pillar_codes = {
                        "p1_domain_solution_depth": "P1",
                        "p2_product_engineering_readiness": "P2",
                        "p3_ai_transparency_trustworthiness": "P3",
                        "p4_business_strategic_fit_for_tcs": "P4",
                        "p5_market_validation_feedback": "P5",
                        "p6_delivery_readiness_risk": "P6"
                    }
                    for p_key, pillar_code in pillar_codes.items():
                        p_data = pillars.get(p_key)
                        if not isinstance(p_data, dict):
                            continue
                        
                        pillar_weight = p_data.get("weight") or 0.0
                        sub_criteria = p_data.get("sub_criteria") or {}
                        
                        for crit_key, crit_val in sub_criteria.items():
                            if not isinstance(crit_val, dict):
                                continue
                            
                            crit_name = crit_key.replace("_", " ").title()
                            assigned_score = crit_val.get("score") or 0.0
                            rationale_text = crit_val.get("reason") or ""
                            confidence_score = crit_val.get("confidence_score") or 0.0
                            weighted_contribution = (float(assigned_score) / 5.0) * float(pillar_weight)
                            
                            logger.info(
                                "Database: Inserting evaluation_criterion_score pillar=%s, criterion=%s, score=%s",
                                pillar_code, crit_key, assigned_score
                            )
                            logger.info(
                                "Database: Evaluation criterion score insert values - pillar_code=%r, criterion_code=%r, criterion_name=%r, assigned_score=%r, pillar_weight_pct=%r, rationale_text=%r, confidence_score=%r, weighted_contribution=%r",
                                pillar_code, crit_key, crit_name, assigned_score, pillar_weight, rationale_text, confidence_score, weighted_contribution
                            )
                            cur.execute(
                                """
                                INSERT INTO evaluation_criterion_scores (
                                    evaluation_criterion_score_id, evaluation_id, pillar_code,
                                    criterion_code, criterion_name, assigned_score, pillar_weight_pct,
                                    significance_level, rationale_text, confidence_score, weighted_contribution,
                                    calculated_by
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                                """,
                                (
                                    str(uuid.uuid4()),
                                    evaluation_id,
                                    pillar_code,
                                    crit_key,
                                    crit_name,
                                    assigned_score,
                                    pillar_weight,
                                    'STANDARD',
                                    rationale_text,
                                    confidence_score,
                                    weighted_contribution,
                                    sys_user_id
                                )
                            )
                
                conn.commit()
                logger.info("Database: Transaction committed. Saved evaluation report. evaluation_id=%s", evaluation_id)
                
        return evaluation_id

    async def save_evaluation_report(
        self,
        *,
        profile_id: str | int,
        evaluation_type: str,
        report_json: dict[str, Any],
    ) -> str:
        self._require_ready()
        return await asyncio.to_thread(
            self._save_evaluation_report_sync,
            profile_id=profile_id,
            evaluation_type=evaluation_type,
            report_json=report_json,
        )


company_profile_db = CompanyProfileDatabase()
