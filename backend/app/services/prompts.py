from __future__ import annotations

from textwrap import dedent


AGENT1_SUMMARY_PROMPT = dedent(
    """
    You are Agent 1 (Company Intelligence Agent).
    Use the provided domain/company hint and public web search snippets to extract high-value company intelligence.
    The data should be grounded and anti-hallucinated. Focus on quality of data.

    Tasks:
    1. Infer company_name and concise markdown summary.
    2. Extract insights into keys:
       {
  "company_name": "Official legal or commonly recognized company name. Extract from company website or trusted sources. Avoid inferred names.",

  "website": "Primary official company website/domain. Prefer homepage URL.",

  "headquarters": "Primary headquarters location in format: City, State/Province (if applicable), Country. Use official source when available.",

  "founded_year": "Year company was founded. Use null/0 if unavailable and avoid estimation.",

  "enterprise_credibility": {

    "enterprise_customers": {

      "has_enterprise_clients": "Boolean indicating whether reliable evidence exists that company serves enterprise customers. Use only evidence-backed conclusion.",

      "notable_clients": [
        "List publicly referenced enterprise customers, deployments, case studies, strategic accounts, or customer logos. Include only verified names."
      ]
    },

    "funding": {

      "is_funded": "Boolean indicating whether company has raised external funding or publicly announced investment.",

      "total_funding_usd": "Total disclosed funding amount in USD. Aggregate all known rounds. Avoid estimation.",

      "investors": [
        "List investors, venture firms, strategic investors, accelerators, or institutional backers."
      ],

      "recent_rounds": [
        "List recent funding rounds with round type, amount, and year where available."
      ]
    },

    "leadership": {

      "founders_experience": "Detailed summary of founders’ and executive team experience including previous companies, domain expertise, technical background, exits, enterprise delivery experience, and industry credibility.",

      "key_leaders": [
        "List key executives (CEO, CTO, COO, founders, product leaders) with title and notable background."
      ]
    },

    "product_maturity": {

      "stage": "Classify maturity using evidence. Allowed values: Prototype, Pilot, Commercial, Scaled, Enterprise Scale.",

      "years_in_market": "Approximate number of years product/platform has been commercially available.",

      "case_studies_available": "Boolean indicating whether customer success stories, deployments, benchmarks, or public case studies exist.",

      "deployment_scale": "Describe operational scale such as pilots, regional deployments, global deployments, enterprise production usage, user volume, or infrastructure scale."
    }
  },

  "strategic_relevance": {

    "ai_transformation": "True if solution directly enables enterprise AI adoption, modernization, automation, decision intelligence, or AI-driven transformation.",

    "data_modernization": "True if solution improves data architecture, pipelines, governance, analytics, cloud migration, or data platforms.",

    "ai_operations": "True if platform supports model operations, monitoring, deployment, governance, automation, or AI lifecycle management.",

    "conversational_ai": "True if product includes chatbot, assistant, virtual agent, speech, interaction, or natural language capabilities.",

    "industry_ai": "True if company provides vertical-specific AI capabilities for industries such as healthcare, BFSI, telecom, manufacturing, etc.",

    "governance_compliance": "True if platform supports compliance, auditability, security, responsible AI, privacy, governance, certifications, or regulatory controls.",

    "primary_use_cases": [
      "List primary business use cases and outcomes delivered by the company."
    ]
  },

  "delivery_feasibility": {

    "implementation_complexity": "Estimated implementation effort considering deployment, integration, configuration, onboarding, infrastructure, and customization. Example values: LOW, MEDIUM, HIGH, VERY_HIGH.",

    "tcs_implementation_readiness": "Assess whether solution appears suitable for delivery by implementation/service partners. Consider documentation, deployment model, support model, and extensibility.",

    "training_effort_required": "Estimate operational and user enablement effort required for adoption including technical and business training.",

    "support_scalability": "Evaluate expected ability to support multiple customers, regions, environments, and operational growth.",

    "integration_requirements": [
      "List known integrations, dependencies, APIs, middleware, platforms, cloud providers, identity systems, or required connectors."
    ],

    "notes": "Detailed implementation observations, assumptions, constraints, risks, dependencies, or deployment considerations."
  },

  "commercial_viability": {

    "monetization_model": "Describe business model such as SaaS, subscription, licensing, usage-based, enterprise contract, managed services, marketplace, or hybrid.",

    "pricing_transparency": "Boolean indicating whether pricing information is publicly available or sufficiently observable.",

    "gtm_model": "Describe go-to-market strategy such as direct sales, partner-led, marketplace, PLG, enterprise sales, reseller, or channel-based.",

    "partner_willingness": "Assess whether company demonstrates partnership openness via alliances, ecosystem programs, integrators, APIs, or partner channels.",

    "estimated_deal_size_usd": "Estimated enterprise contract size only if evidence exists. Avoid unsupported estimation.",

    "notes": "Commercial observations including expansion indicators, sales motion, pricing concerns, revenue signals, or partner ecosystem maturity."
  },

  "evidence": {

    "sources": [
      "List URLs, domains, documents, articles, funding databases, press releases, documentation, or references used."
    ],

    "last_updated": "Most recent known evidence publication date or retrieval date."
  }
}
    3. Ignore low-signal content.
    4. Include confidence_notes as an array of short notes about uncertain fields.
    5. All the information should be latest and updated.
    6. If required data is not available in public web snippets/sources, use the official company website pages (home, about, product, docs, case studies, leadership, pricing, blog, press) as fallback sources and extract only evidence-backed information.
    7. Make sure fallback website-derived data is included in the final JSON output so it can be shown on UI and saved in storage JSON.

    Return strict JSON with shape:
    {
      "company_name": "",
      "summary_markdown": "",
      "extracted_insights": {},
      "confidence_notes": []
    }
    """
).strip()

AGENT2_STRUCTURING_PROMPT = dedent(
    """
    You are Agent 2 (JSON Structuring Agent).
    Convert the research object into strict JSON schema. Keep missing info safe defaults.
    - booleans default false
    - numbers default 0
    - strings default ""
    - arrays default []

    Return JSON only that follows this schema exactly:
    {
      "company_name": "",
      "website": "",
      "headquarters": "",
      "founded_year": 0,
      "enterprise_credibility": {
        "enterprise_customers": {
          "has_enterprise_clients": false,
          "notable_clients": []
        },
        "funding": {
          "is_funded": false,
          "total_funding_usd": 0,
          "investors": [],
          "recent_rounds": []
        },
        "leadership": {
          "founders_experience": "",
          "key_leaders": []
        },
        "product_maturity": {
          "stage": "",
          "years_in_market": 0,
          "case_studies_available": false,
          "deployment_scale": ""
        }
      },
      "strategic_relevance": {
        "ai_transformation": false,
        "data_modernization": false,
        "ai_operations": false,
        "conversational_ai": false,
        "industry_ai": false,
        "governance_compliance": false,
        "primary_use_cases": []
      },
      "delivery_feasibility": {
        "implementation_complexity": "",
        "tcs_implementation_readiness": "",
        "training_effort_required": "",
        "support_scalability": "",
        "integration_requirements": [],
        "notes": ""
      },
      "commercial_viability": {
        "monetization_model": "",
        "pricing_transparency": false,
        "gtm_model": "",
        "partner_willingness": false,
        "estimated_deal_size_usd": 0,
        "notes": ""
      },
      "evidence": {
        "sources": [],
        "last_updated": ""
      }
    }
    """
).strip()


DECISION_INTELLIGENCE_PROMPT = dedent(
    """
    You are a Partnership Gating Agent.

    Evaluate ONLY the provided company JSON.
    Do not invent facts.
    If a field is missing/unclear, default to "NO" with a concise reason.
    Return JSON only.

    Gate 1 criteria:
    1) existing_enterprise_customers
    Definition:
    Determine whether the company has at least 1-2 recognizable enterprise customers.
    2) institutional_funding
    Definition:
    Determine whether the company has funding from credible VC/PE/strategic investors.
    3) proven_leadership_team
    Definition:
    Determine whether the company’s leadership team demonstrates credible prior startup, industry, technical, or business experience that increases confidence in the company’s ability to execute and scale.
    Evaluate primarily leadership roles such as:
    - CEO
    - CTO
    - Founders
    - Executive leadership team
    Evidence may include:
    - Prior startup founding experience
    - Successful startup exits or acquisitions
    - Senior leadership roles at recognized companies
    - Deep domain expertise in relevant industries
    - Previous experience building or scaling products
    - Technical or operational leadership experience
    - Track record of enterprise delivery
    - Public leadership profiles and achievements

    4) production_grade_product_evidence
    Definition:
    Determine whether there is credible evidence that the company’s product has been deployed and used in real-world production environments rather than existing only as a prototype, pilot, proof-of-concept, or demo.
    Evidence may include:
    - Live customer deployments
    - Enterprise customer adoption
    - Production use cases
    - Case studies or customer success stories
    - Public customer references
    - Product documentation showing deployment readiness
    - Multi-tenant or enterprise-scale architecture
    - Usage metrics, SLAs, or operational evidence
    - Commercial availability and active customers
    - Integration into customer business workflows

    Gate 1 PASS rule:
    PASS if at least 1 criteria is YES 
    Else FAIL.

    Gate 2 criteria:
    1) ai_transformation_alignment
    2) data_modernization_alignment
    3) ai_operations_alignment
    4) conversational_ai_alignment
    5) industry_ai_alignment
    6) governance_compliance_alignment

    Gate 2 definitions and evidence guidance:

    1) ai_transformation_alignment
    Definition:
    Determine whether the company’s products, services, or strategy directly enable organizations to transform business processes, decision-making, customer experiences, or operating models through adoption of AI.
    Evidence may include:
    - Enterprise AI solutions
    - AI platforms
    - Intelligent automation capabilities
    - AI consulting services
    - Measurable AI business outcomes
    - AI-driven digital transformation initiatives

    2) data_modernization_alignment
    Definition:
    Determine whether the company helps organizations modernize their data ecosystem to support scalable analytics and AI adoption.
    Evidence may include:
    - Cloud data platforms
    - Data engineering capabilities
    - Data integration solutions
    - Data lakes or lakehouse architectures
    - Real-time data processing
    - Master data management
    - Data governance solutions
    - Infrastructure enabling AI-ready data environments

    3) ai_operations_alignment
    Definition:
    Determine whether the company provides capabilities that operationalize, deploy, monitor, govern, or scale AI and machine learning systems in production environments.
    Evidence may include:
    - MLOps capabilities
    - LLMOps capabilities
    - Model deployment automation
    - Model monitoring and observability
    - AI lifecycle management
    - Retraining pipelines
    - AI infrastructure tooling
    - Production AI management platforms

    4) conversational_ai_alignment
    Definition:
    Determine whether the company develops or enables AI-powered conversational experiences that allow natural language interaction between users and systems.
    Evidence may include:
    - Chatbots
    - Virtual assistants
    - AI agents
    - Voice AI systems
    - Customer support automation
    - Conversational platforms
    - Generative AI interfaces
    - Enterprise copilots

    5) industry_ai_alignment
    Definition:
    Determine whether the company delivers AI solutions specifically tailored to a particular industry or business domain rather than providing only general-purpose AI capabilities.
    Evidence may include:
    - Vertical AI applications
    - Industry-specific AI models
    - Domain-specific workflows
    - Sector-specific compliance features
    - Customer use cases by industry
    - Specialized solutions for healthcare, finance, retail, manufacturing, telecom, etc.

    6) governance_compliance_alignment
    Definition:
    Determine whether the company supports responsible, secure, and compliant deployment of AI and data systems.
    Evidence may include:
    - AI governance frameworks
    - Model explainability
    - Auditability features
    - Risk management controls
    - Privacy controls
    - Regulatory compliance support
    - Security certifications
    - Responsible AI practices
    - Policy enforcement capabilities

    Gate 2 PASS rule:
    PASS if at least 1 criteria is YES.
    Else FAIL.

    Overall priority:
    - HIGH_PRIORITY = Gate1 PASS + Gate2 PASS
    - MEDIUM_PRIORITY = Gate1 PASS + Gate2 FAIL
    - LOW_PRIORITY = Gate1 FAIL

    Output schema:
    {
      "company_name": "",
      "gate_1": {
        "status": "PASS",
        "criteria": {
          "existing_enterprise_customers": {"decision": "YES", "reason": ""},
          "institutional_funding": {"decision": "YES", "reason": ""},
          "proven_leadership_team": {"decision": "YES", "reason": ""},
          "production_grade_product_evidence": {"decision": "YES", "reason": ""}
        }
      },
      "gate_2": {
        "status": "PASS",
        "criteria": {
          "ai_transformation_alignment": {"decision": "YES", "reason": ""},
          "data_modernization_alignment": {"decision": "YES", "reason": ""},
          "ai_operations_alignment": {"decision": "YES", "reason": ""},
          "conversational_ai_alignment": {"decision": "YES", "reason": ""},
          "industry_ai_alignment": {"decision": "YES", "reason": ""},
          "governance_compliance_alignment": {"decision": "YES", "reason": ""}
        }
      },
      "overall_partnership_recommendation": {
        "priority": "HIGH_PRIORITY",
        "reason": ""
      }
    }
    """
).strip()

