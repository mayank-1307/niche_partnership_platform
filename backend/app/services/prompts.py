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
    Convert the research object into a gate-first analysis JSON. Keep missing info safe defaults.
    - strings default ""
    - numbers default 0
    - arrays default []
    - every sub-part must include:
      - "facts": object with the extracted data supporting that sub-part
    - each gate section must include a top-level `sources` array with only the most relevant URLs/domains for that gate
    - do not put sources on sub-parts
    - Use the gate structure below exactly. Do not output the old first-draft company JSON.

    Return JSON only that follows this schema exactly:
    {
      "company_name": "",
      "website": "",
      "headquarters": "",
      "founded_year": 0,
      "enterprise_credibility": {
        "sources": [],
        "sub_parts": {
          "existing_enterprise_customers": {
            "facts": {
              "has_enterprise_clients": false,
              "notable_clients": []
            }
          },
          "institutional_funding": {
            "facts": {
              "is_funded": false,
              "total_funding_usd": 0,
              "investors": [],
              "recent_rounds": []
            }
          },
          "proven_leadership_team": {
            "facts": {
              "founders_experience": "",
              "key_leaders": []
            }
          },
          "production_grade_product_evidence": {
            "facts": {
              "stage": "",
              "years_in_market": 0,
              "case_studies_available": false,
              "deployment_scale": ""
            }
          }
        }
      },
      "strategic_relevance": {
        "sources": [],
        "sub_parts": {
          "ai_transformation_alignment": {
            "facts": {
              "ai_transformation": false,
              "use_cases": []
            }
          },
          "data_modernization_alignment": {
            "facts": {
              "data_modernization": false,
              "platforms": [],
              "capabilities": []
            }
          },
          "ai_operations_alignment": {
            "facts": {
              "ai_operations": false,
              "capabilities": []
            }
          },
          "conversational_ai_alignment": {
            "facts": {
              "conversational_ai": false,
              "interfaces": []
            }
          },
          "industry_ai_alignment": {
            "facts": {
              "industry_ai": false,
              "verticals": []
            }
          },
          "governance_compliance_alignment": {
            "facts": {
              "governance_compliance": false,
              "controls": [],
              "certifications": []
            }
          }
        }
      },
      "delivery_feasibility": {
        "sources": [],
        "delivery_feasibility": {
          "skill_availability": {
            "facts": {
              "implementation_complexity": "",
              "available_skills": [],
              "required_skills": [],
              "gap_notes": ""
            }
          },
          "training_effort": {
            "facts": {
              "training_effort_required": "",
              "ramp_time": "",
              "training_needs": []
            }
          },
          "integration_feasibility": {
            "facts": {
              "integration_requirements": [],
              "dependencies": [],
              "complexity_notes": ""
            }
          },
          "support_scalability": {
            "facts": {
              "support_scalability": "",
              "support_model": "",
              "scaling_constraints": []
            }
          }
        }
      },
      "commercial_viability": {
        "sources": [],
        "sub_parts": {
          "monetization_clarity": {
            "facts": {
              "monetization_model": "",
              "pricing_transparency": false,
              "revenue_structure": ""
            }
          },
          "gtm_feasibility": {
            "facts": {
              "gtm_model": "",
              "channels": [],
              "sales_motion": ""
            }
          },
          "revenue_upside": {
            "facts": {
              "estimated_deal_size_usd": 0,
              "expansion_paths": []
            }
          },
          "partner_willingness": {
            "facts": {
              "partner_willingness": false,
              "partner_programs": [],
              "api_ecosystem": []
            }
          },
          "commercial_structure_clarity": {
            "facts": {
              "contracting_notes": "",
              "pricing_governance": ""
            }
          },
          "startup_stage_fit": {
            "facts": {
              "stage": "",
              "fit_notes": ""
            }
          }
        }
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
    Add a concise summary for each gate. Keep it 1-2 sentences and based only on the evidence provided.

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

    Gate 3 criteria (Delivery Feasibility):
    Role and context:
    - Act as an enterprise solution architect and partnership evaluation expert.
    - Evaluate delivery feasibility for partnerships between:
      - Company X: implementation/service provider
      - Company Y: solution/vendor being evaluated
    - Assume enterprise scenarios across software, cloud, data, and GenAI systems, including APIs, databases, agents, and enterprise platforms.

    Evaluation objective:
    Assess whether Company X can effectively deliver, integrate, support, and scale Company Y's solution in an enterprise environment.

    1) skill_availability
    Definition:
    Evaluate whether required capabilities to implement the solution are readily available within Company X or can be developed quickly using standard industry skills.
    Consider:
    - Cloud skills (AWS, Azure, GCP)
    - Database experience (SQL, NoSQL)
    - Experience with GenAI, agents, and APIs
    - Familiarity with enterprise platforms
    - Need for niche or proprietary expertise
    Question:
    Does the implementation provider have or can easily build capability?
    Allowed decision options:
    - YES
    - PARTIAL
    - NO

    2) training_effort
    Definition:
    Assess whether effort required to train teams is manageable within a reasonable timeline.
    Consider:
    - Learning curve of the solution
    - Availability and quality of documentation
    - Dependency on vendor-led training
    - Ease of onboarding new developers and delivery teams
    Question:
    Is training effort manageable within reasonable time?
    Allowed decision options:
    - YES
    - HIGH
    - NO

    3) integration_feasibility
    Definition:
    Evaluate how easily the solution can integrate into enterprise systems and workflows.
    Focus on:
    - API availability and compatibility
    - Data layer integration (databases, warehouses, data lakes)
    - Security and compliance constraints
    - Workflow and platform embedding
    Question:
    Can it integrate into enterprise stacks (data, apps)?
    Allowed decision options:
    - YES
    - COMPLEX
    - NO

    4) support_scalability
    Definition:
    Evaluate ability to operate, maintain, and scale the solution reliably across users, use cases, and workloads.
    Includes:
    - Performance and capacity scaling
    - Monitoring and support operating model
    - Cost management at scale
    - Incident handling and production reliability
    Question:
    Can the implementation provider support it at scale post-deployment?
    Allowed decision options:
    - YES
    - PARTIAL
    - NO

    Gate 3 decision rule:
    - PASS: Mostly YES and manageable delivery feasibility.
    - DEFER: Mixed result (YES + PARTIAL/COMPLEX/HIGH) that is feasible with mitigation.
    - FAIL: Majority NO or clearly non-manageable feasibility.

    Gate 4 criteria (Commercial Viability):
    1) monetization_clarity
    Definition:
    Evaluate whether the revenue model is clearly defined and understandable.
    Consider:
    - Pricing model (subscription, usage-based, license)
    - Transparency of pricing
    - Ease of explaining value to customers
    - Predictability of revenue streams
    Question:
    Is there a clear revenue model (services/license/AI-as-a-service)?
    Requirement: Required
    Allowed decision options:
    - YES
    - NO

    2) gtm_feasibility
    Definition:
    Assess whether the solution can be effectively positioned, sold, and distributed in the market.
    Consider:
    - Fit with existing sales channels
    - Target customer segments (enterprise, SMB, industry-specific)
    - Sales complexity
    - Need for specialized sales motion
    Question:
    Can it be sold through Company X channels (clients, industries)?
    Requirement: Required
    Allowed decision options:
    - YES
    - NO

    3) revenue_upside
    Definition:
    Evaluate the potential revenue opportunity from the partnership.
    Consider:
    - Market demand for the solution
    - Cross-sell / upsell opportunities
    - Scalability of deal sizes
    - Long-term revenue potential
    Question:
    Is there meaningful deal size / scalability?
    Requirement: Required
    Allowed decision options:
    - YES
    - NO

    4) partner_willingness
    Definition:
    Assess whether Company Y is open and capable of forming a strong partnership.
    Consider:
    - Openness to collaboration
    - Partner programs or ecosystem presence
    - Co-selling / co-development readiness
    - Flexibility in engagement
    Question:
    Is the company open to co-sell / co-build / alliance?
    Requirement: Required
    Allowed decision options:
    - YES
    - NO

    5) commercial_structure_clarity
    Definition:
    Evaluate whether the commercial terms and engagement model are well-defined and manageable.
    Consider:
    - Contract clarity
    - Revenue sharing model (if applicable)
    - Pricing governance
    - Legal and compliance simplicity
    Question:
    Is pricing understandable and workable?
    Requirement: Required
    Allowed decision options:
    - YES
    - NO

    6) startup_stage_fit
    Definition:
    Assess whether the maturity level of Company Y aligns with the scale and expectations of enterprise delivery.
    Consider:
    - Company maturity (startup vs established)
    - Stability of product and roadmap
    - Risk associated with early-stage companies
    - Ability to support enterprise clients
    Question:
    Not too early (immature) or too mature (SI competitor)?
    Requirement: Required
    Allowed decision options:
    - YES
    - NO

    Gate 4 decision rule:
    - PASS: ALL criteria are YES.
    - FAIL: ANY criteria is NO.

    Overall priority:
    - HIGH_PRIORITY = Gate1 PASS + Gate2 PASS + Gate3 PASS + Gate4 PASS
    - MEDIUM_PRIORITY = Gate1 PASS and (Gate2 FAIL or Gate3 DEFER) and Gate4 PASS
    - LOW_PRIORITY = Gate1 FAIL or Gate3 FAIL or Gate4 FAIL
    - The overall_partnership_recommendation.reason should be 1-2 sentences that summarize the business case, main strengths, and main risks.
    - Mention the most important gate outcomes and the key criteria driving the recommendation.

    Output schema:
    {
      "company_name": "",
      "gate_1": {
        "status": "PASS",
        "summary": "",
        "criteria": {
          "existing_enterprise_customers": {"decision": "YES", "reason": "", "confidence_score": 0},
          "institutional_funding": {"decision": "YES", "reason": "", "confidence_score": 0},
          "proven_leadership_team": {"decision": "YES", "reason": "", "confidence_score": 0},
          "production_grade_product_evidence": {"decision": "YES", "reason": "", "confidence_score": 0}
        }
      },
      "gate_2": {
        "status": "PASS",
        "summary": "",
        "criteria": {
          "ai_transformation_alignment": {"decision": "YES", "reason": "", "confidence_score": 0},
          "data_modernization_alignment": {"decision": "YES", "reason": "", "confidence_score": 0},
          "ai_operations_alignment": {"decision": "YES", "reason": "", "confidence_score": 0},
          "conversational_ai_alignment": {"decision": "YES", "reason": "", "confidence_score": 0},
          "industry_ai_alignment": {"decision": "YES", "reason": "", "confidence_score": 0},
          "governance_compliance_alignment": {"decision": "YES", "reason": "", "confidence_score": 0}
        }
      },
      "gate_3": {
        "status": "PASS",
        "summary": "",
        "criteria": {
          "skill_availability": {"decision": "YES", "reason": "", "confidence_score": 0},
          "training_effort": {"decision": "YES", "reason": "", "confidence_score": 0},
          "integration_feasibility": {"decision": "YES", "reason": "", "confidence_score": 0},
          "support_scalability": {"decision": "YES", "reason": "", "confidence_score": 0}
        }
      },
      "gate_4": {
        "status": "PASS",
        "summary": "",
        "criteria": {
          "monetization_clarity": {"decision": "YES", "reason": "", "confidence_score": 0},
          "gtm_feasibility": {"decision": "YES", "reason": "", "confidence_score": 0},
          "revenue_upside": {"decision": "YES", "reason": "", "confidence_score": 0},
          "partner_willingness": {"decision": "YES", "reason": "", "confidence_score": 0},
          "commercial_structure_clarity": {"decision": "YES", "reason": "", "confidence_score": 0},
          "startup_stage_fit": {"decision": "YES", "reason": "", "confidence_score": 0}
        }
      },
      "overall_partnership_recommendation": {
        "priority": "HIGH_PRIORITY",
        "reason": ""
      }
    }
    """
).strip()


SCORING_PROMPT = dedent(
    """
    You are an enterprise solution architect and partnership evaluation expert.

    Evaluate ONLY the provided company JSON and return JSON only.
    Do not invent facts. If evidence is weak or missing, use lower scores.

    Scoring pillars and weights:
    - P1 Domain & Solution Depth: weight 25
    - P2 Product & Engineering Readiness: weight 15
    - P3 AI Transparency & Trustworthiness: weight 10

    Scoring rules:
    - Most sub-criteria are scored from 0 to 5.
    - P1.4 is binary only: 0 or 5.
    - Each pillar raw score is average of its sub-criteria (0-5 scale).
    - Each pillar weighted score = (pillar_raw_score / 5) * pillar_weight.
    - total_weighted_score = sum of the three weighted pillar scores.
    - Do not invent or override total_weighted_score; it must equal the computed sum of the three pillars.
    - Keep reasons concise and evidence-oriented.
    - Add confidence_score to every sub-criterion as an integer from 0 to 100 based on evidence quality and completeness.
    - Use the full 0-100 scale. Do not output 0/1 confidence values.

    Output schema:
    {
      "company_name": "",
      "pillars": {
        "p1_domain_solution_depth": {
          "weight": 25,
          "raw_score": 0,
          "weighted_score": 0,
          "summary": "",
          "sub_criteria": {
            "p1_1_domain_specific_problem_ownership": {"score": 0, "reason": "", "confidence_score": 0},
            "p1_2_decision_outcome_orientation": {"score": 0, "reason": "", "confidence_score": 0},
            "p1_3_embedded_domain_logic": {"score": 0, "reason": "", "confidence_score": 0},
            "p1_4_not_generic_platform_building_block": {"score": 0, "reason": "", "confidence_score": 0},
            "p1_5_degree_of_workflow_ownership": {"score": 0, "reason": "", "confidence_score": 0}
          }
        },
        "p2_product_engineering_readiness": {
          "weight": 15,
          "raw_score": 0,
          "weighted_score": 0,
          "summary": "",
          "sub_criteria": {
            "p2_1_scalability_performance": {"score": 0, "reason": "", "confidence_score": 0},
            "p2_2_mlops_maturity": {"score": 0, "reason": "", "confidence_score": 0},
            "p2_3_security_compliance_readiness": {"score": 0, "reason": "", "confidence_score": 0},
            "p2_4_deployment_flexibility": {"score": 0, "reason": "", "confidence_score": 0},
            "p2_5_api_ecosystem_interoperability": {"score": 0, "reason": "", "confidence_score": 0}
          }
        },
        "p3_ai_transparency_trustworthiness": {
          "weight": 10,
          "raw_score": 0,
          "weighted_score": 0,
          "summary": "",
          "sub_criteria": {
            "p3_1_explainability_of_outcomes": {"score": 0, "reason": "", "confidence_score": 0},
            "p3_2_model_transparency": {"score": 0, "reason": "", "confidence_score": 0},
            "p3_3_bias_hallucination_controls": {"score": 0, "reason": "", "confidence_score": 0},
            "p3_4_human_in_the_loop_support": {"score": 0, "reason": "", "confidence_score": 0},
            "p3_5_identity_data_protection": {"score": 0, "reason": "", "confidence_score": 0}
          }
        },
      },
      "total_weighted_score": 0,
      "overall_summary": ""
    }
    """
).strip()

SCORING_PROMPT_P456 = dedent(
    """
    You are an enterprise solution architect and partnership evaluation expert.

    Evaluate ONLY the provided company JSON and return JSON only.
    Do not invent facts. If evidence is weak or missing, use lower scores.

    Scoring pillars and weights:
    - P4 Business & Strategic Fit for TCS: weight 20
    - P5 Market Validation & Feedback: weight 15
    - P6 Delivery Readiness & Risk: weight 15

    Scoring rules:
    - Most sub-criteria are scored from 0 to 5.
    - P4.4 is binary only: 0 or 5.
    - P5.3 is discrete only: 0, 3, or 5.
    - P5.4 is discrete only: 0, 1, 3, or 5.
    - P6.4 is discrete only: 0, 1, 3, or 5.
    - Each pillar raw score is average of its sub-criteria (0-5 scale).
    - Each pillar weighted score = (pillar_raw_score / 5) * pillar_weight.
    - total_weighted_score = sum of the three weighted pillar scores.
    - Do not invent or override total_weighted_score; it must equal the computed sum of the three pillars.
    - Keep reasons concise and evidence-oriented.
    - Add confidence_score to every sub-criterion as an integer from 0 to 100 based on evidence quality and completeness.
    - Use the full 0-100 scale. Do not output 0/1 confidence values.

    Output schema:
    {
      "company_name": "",
      "pillars": {
        "p4_business_strategic_fit_for_tcs": {
          "weight": 20,
          "raw_score": 0,
          "weighted_score": 0,
          "summary": "",
          "sub_criteria": {
            "p4_1_cost_transparency": {"score": 0, "reason": "", "confidence_score": 0},
            "p4_2_measurable_roi": {"score": 0, "reason": "", "confidence_score": 0},
            "p4_3_value_capture_for_tcs": {"score": 0, "reason": "", "confidence_score": 0},
            "p4_4_ip_ownership_clarity": {"score": 0, "reason": "", "confidence_score": 0},
            "p4_5_scalability_via_tcs": {"score": 0, "reason": "", "confidence_score": 0},
            "p4_6_strategic_ai_alignment": {"score": 0, "reason": "", "confidence_score": 0},
            "p4_7_future_trajectory": {"score": 0, "reason": "", "confidence_score": 0},
            "p4_8_time_to_value": {"score": 0, "reason": "", "confidence_score": 0}
          }
        },
        "p5_market_validation_feedback": {
          "weight": 15,
          "raw_score": 0,
          "weighted_score": 0,
          "summary": "",
          "sub_criteria": {
            "p5_1_analyst_recognition": {"score": 0, "reason": "", "confidence_score": 0},
            "p5_2_market_sentiment": {"score": 0, "reason": "", "confidence_score": 0},
            "p5_3_customer_references_discrete": {"score": 0, "reason": "", "confidence_score": 0},
            "p5_4_active_deal_pipeline_discrete": {"score": 0, "reason": "", "confidence_score": 0}
          }
        },
        "p6_delivery_readiness_risk": {
          "weight": 15,
          "raw_score": 0,
          "weighted_score": 0,
          "summary": "",
          "sub_criteria": {
            "p6_1_skill_availability": {"score": 0, "reason": "", "confidence_score": 0},
            "p6_2_training_effort": {"score": 0, "reason": "", "confidence_score": 0},
            "p6_3_integration_complexity": {"score": 0, "reason": "", "confidence_score": 0},
            "p6_4_delivery_risk_discrete": {"score": 0, "reason": "", "confidence_score": 0},
            "p6_5_data_dependency_readiness": {"score": 0, "reason": "", "confidence_score": 0},
            "p6_6_number_of_employees": {"score": 0, "reason": "", "confidence_score": 0}
          }
        }
      },
      "total_weighted_score": 0,
      "overall_summary": ""
    }
    """
).strip()

