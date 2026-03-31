import itertools
from wargame.models.agent_response import AgentResponse, ActionType
from wargame.providers.base import BaseLLMProvider

MOCK_RESPONSES: dict[str, list[AgentResponse]] = {
    "developer": [
        AgentResponse(agent_id="developer", turn=0, sprint=1, action=ActionType.COMPLETE,
                      rationale="Implemented API Gateway configuration on Azure APIM with routing rules.",
                      referenced_stories=["HU-001"], confidence=0.9, tech_debt_added=0),
        AgentResponse(agent_id="developer", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="Code review passed, PR ready for merge. All unit tests green.",
                      referenced_stories=["HU-002"], confidence=0.85, tech_debt_added=0),
        AgentResponse(agent_id="developer", turn=0, sprint=1, action=ActionType.IDLE,
                      rationale="Waiting for QA sign-off on HU-003 before proceeding.",
                      referenced_stories=["HU-003"], confidence=0.7, tech_debt_added=0),
        AgentResponse(agent_id="developer", turn=0, sprint=1, action=ActionType.ESCALATE,
                      rationale="Legacy Oracle stored procedure is undocumented; need Tech Lead input.",
                      referenced_stories=["HU-011"], confidence=0.6, tech_debt_added=3),
        AgentResponse(agent_id="developer", turn=0, sprint=1, action=ActionType.COMPLETE,
                      rationale="Completed schema migration script for EPIC-02 with rollback support.",
                      referenced_stories=["HU-012"], confidence=0.88, tech_debt_added=0),
    ],
    "qa_engineer": [
        AgentResponse(agent_id="qa_engineer", turn=0, sprint=1, action=ActionType.BLOCK_DONE,
                      rationale="HU-001 fails integration test: API Gateway returns 503 under load. Cannot mark done.",
                      referenced_stories=["HU-001"], confidence=0.95, tech_debt_added=0),
        AgentResponse(agent_id="qa_engineer", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="All 45 test cases pass for HU-002. Coverage at 82%. Approved.",
                      referenced_stories=["HU-002"], confidence=0.9, tech_debt_added=0),
        AgentResponse(agent_id="qa_engineer", turn=0, sprint=1, action=ActionType.BLOCK_DONE,
                      rationale="Missing regression suite for Oracle migration path. Blocking until tests added.",
                      referenced_stories=["HU-011"], confidence=0.92, tech_debt_added=0),
        AgentResponse(agent_id="qa_engineer", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="Smoke tests pass. Performance within SLA bounds. Approved for staging.",
                      referenced_stories=["HU-003"], confidence=0.88, tech_debt_added=0),
        AgentResponse(agent_id="qa_engineer", turn=0, sprint=1, action=ActionType.IDLE,
                      rationale="No stories in IN_REVIEW state this turn. Standing by.",
                      referenced_stories=[], confidence=0.8, tech_debt_added=0),
    ],
    "tech_lead": [
        AgentResponse(agent_id="tech_lead", turn=0, sprint=1, action=ActionType.VETO,
                      rationale="HU-001 PR uses deprecated APIM policy syntax. Must refactor before merge.",
                      referenced_stories=["HU-001"], confidence=0.95, tech_debt_added=0),
        AgentResponse(agent_id="tech_lead", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="Architecture for microservice decomposition is sound. Approved.",
                      referenced_stories=["HU-002"], confidence=0.9, tech_debt_added=0),
        AgentResponse(agent_id="tech_lead", turn=0, sprint=1, action=ActionType.ESCALATE,
                      rationale="Oracle PL/SQL migration risk is underestimated. Needs Security Architect review.",
                      referenced_stories=["HU-011"], confidence=0.85, tech_debt_added=5),
        AgentResponse(agent_id="tech_lead", turn=0, sprint=1, action=ActionType.VETO,
                      rationale="Hardcoded credentials found in CI script. Cannot proceed without secret management.",
                      referenced_stories=["HU-021"], confidence=0.98, tech_debt_added=0),
        AgentResponse(agent_id="tech_lead", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="Strangler fig pattern implementation looks correct. Good isolation boundaries.",
                      referenced_stories=["HU-003"], confidence=0.88, tech_debt_added=0),
    ],
    "product_owner": [
        AgentResponse(agent_id="product_owner", turn=0, sprint=1, action=ActionType.REPRIORITIZE,
                      rationale="Business stakeholders require customer portal stories done before pipeline work.",
                      referenced_stories=["HU-001", "HU-002"], confidence=0.8, tech_debt_added=0),
        AgentResponse(agent_id="product_owner", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="Sprint goal alignment confirmed. All committed stories map to business value.",
                      referenced_stories=["HU-001"], confidence=0.85, tech_debt_added=0),
        AgentResponse(agent_id="product_owner", turn=0, sprint=1, action=ActionType.REPRIORITIZE,
                      rationale="Compliance deadline moved up — GDPR stories must be in this sprint.",
                      referenced_stories=["HU-015", "HU-016"], confidence=0.75, tech_debt_added=0),
        AgentResponse(agent_id="product_owner", turn=0, sprint=1, action=ActionType.ESCALATE,
                      rationale="Team velocity too low for committed scope. Escalating to management.",
                      referenced_stories=["HU-001", "HU-011"], confidence=0.7, tech_debt_added=0),
        AgentResponse(agent_id="product_owner", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="Sprint review feedback positive. Proceeding with current backlog order.",
                      referenced_stories=[], confidence=0.82, tech_debt_added=0),
    ],
    "security_architect": [
        AgentResponse(agent_id="security_architect", turn=0, sprint=1, action=ActionType.FLAG,
                      rationale="APIM configuration exposes internal service endpoints. PCI-DSS violation risk.",
                      referenced_stories=["HU-001"], confidence=0.93, tech_debt_added=0),
        AgentResponse(agent_id="security_architect", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="OAuth2 implementation reviewed. Follows GDPR data minimization principles.",
                      referenced_stories=["HU-005"], confidence=0.88, tech_debt_added=0),
        AgentResponse(agent_id="security_architect", turn=0, sprint=1, action=ActionType.FLAG,
                      rationale="Oracle migration script logs sensitive PII to stdout. Must be remediated.",
                      referenced_stories=["HU-011"], confidence=0.97, tech_debt_added=8),
        AgentResponse(agent_id="security_architect", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="Key Vault integration reviewed. Secrets management meets compliance bar.",
                      referenced_stories=["HU-021"], confidence=0.91, tech_debt_added=0),
        AgentResponse(agent_id="security_architect", turn=0, sprint=1, action=ActionType.IDLE,
                      rationale="No security-relevant changes in this turn. Monitoring.",
                      referenced_stories=[], confidence=0.85, tech_debt_added=0),
    ],
    "cloud_engineer": [
        AgentResponse(agent_id="cloud_engineer", turn=0, sprint=1, action=ActionType.COMPLETE,
                      rationale="AKS cluster provisioned with autoscaling. Terraform state stored in Azure Blob.",
                      referenced_stories=["HU-021"], confidence=0.87, tech_debt_added=0),
        AgentResponse(agent_id="cloud_engineer", turn=0, sprint=1, action=ActionType.BLOCK_DONE,
                      rationale="Azure DevOps service connection not authorized. Blocking pipeline story.",
                      referenced_stories=["HU-022"], confidence=0.9, tech_debt_added=0),
        AgentResponse(agent_id="cloud_engineer", turn=0, sprint=1, action=ActionType.COMPLETE,
                      rationale="Helm chart deployed to staging namespace. Health checks passing.",
                      referenced_stories=["HU-023"], confidence=0.85, tech_debt_added=2),
        AgentResponse(agent_id="cloud_engineer", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="IaC reviewed. No drift detected between Terraform plan and actual resources.",
                      referenced_stories=["HU-021"], confidence=0.88, tech_debt_added=0),
        AgentResponse(agent_id="cloud_engineer", turn=0, sprint=1, action=ActionType.ESCALATE,
                      rationale="Azure subscription quota exceeded for AKS node pools. Need approval for increase.",
                      referenced_stories=["HU-024"], confidence=0.8, tech_debt_added=0),
    ],
    "scrum_master": [
        AgentResponse(agent_id="scrum_master", turn=0, sprint=1, action=ActionType.IMPEDIMENT,
                      rationale="Tech Lead and Product Owner in conflict over scope. Facilitating resolution.",
                      referenced_stories=[], confidence=0.88, tech_debt_added=0),
        AgentResponse(agent_id="scrum_master", turn=0, sprint=1, action=ActionType.IDLE,
                      rationale="Team flow is healthy. No blockers detected. Velocity on track.",
                      referenced_stories=[], confidence=0.82, tech_debt_added=0),
        AgentResponse(agent_id="scrum_master", turn=0, sprint=1, action=ActionType.IMPEDIMENT,
                      rationale="Developer waiting 3 days for QA feedback. Raising impediment to unblock.",
                      referenced_stories=["HU-001"], confidence=0.9, tech_debt_added=0),
        AgentResponse(agent_id="scrum_master", turn=0, sprint=1, action=ActionType.ESCALATE,
                      rationale="Sprint burndown shows 40% remaining with 2 days left. Escalating to management.",
                      referenced_stories=[], confidence=0.85, tech_debt_added=0),
        AgentResponse(agent_id="scrum_master", turn=0, sprint=1, action=ActionType.IMPEDIMENT,
                      rationale="Security review bottleneck: 5 stories waiting for security_architect sign-off.",
                      referenced_stories=["HU-005", "HU-011"], confidence=0.87, tech_debt_added=0),
    ],
    "software_architect": [
        AgentResponse(agent_id="software_architect", turn=0, sprint=1, action=ActionType.FLAG,
                      rationale="Microservice boundary for customer portal violates bounded context principles.",
                      referenced_stories=["HU-002"], confidence=0.88, tech_debt_added=5),
        AgentResponse(agent_id="software_architect", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="Event-driven architecture for Oracle migration aligns with long-term vision.",
                      referenced_stories=["HU-011"], confidence=0.85, tech_debt_added=0),
        AgentResponse(agent_id="software_architect", turn=0, sprint=1, action=ActionType.VETO,
                      rationale="Proposed synchronous REST calls between microservices violates resilience ADR-001.",
                      referenced_stories=["HU-003"], confidence=0.92, tech_debt_added=0),
        AgentResponse(agent_id="software_architect", turn=0, sprint=1, action=ActionType.COMPLETE,
                      rationale="ADR-002 published: async messaging via Azure Service Bus for all inter-service comms.",
                      referenced_stories=["HU-004"], confidence=0.9, artifacts=["ADR-002"], tech_debt_added=0),
        AgentResponse(agent_id="software_architect", turn=0, sprint=1, action=ActionType.APPROVE,
                      rationale="Domain model reviewed. Strangler fig decomposition follows hexagonal architecture.",
                      referenced_stories=["HU-001"], confidence=0.87, tech_debt_added=0),
    ],
}

_counters: dict[str, itertools.cycle] = {
    role: itertools.cycle(range(len(responses)))
    for role, responses in MOCK_RESPONSES.items()
}


class MockProvider(BaseLLMProvider):
    provider_name = "mock"

    async def complete(self, system_prompt: str, user_prompt: str) -> AgentResponse:
        # Identify role from user_prompt only (system_prompt may mention other roles as words)
        role = "developer"
        for r in MOCK_RESPONSES:
            if r in user_prompt.lower():
                role = r
                break
        idx = next(_counters[role])
        base = MOCK_RESPONSES[role][idx]
        return base.model_copy()

    def is_available(self) -> bool:
        return True
