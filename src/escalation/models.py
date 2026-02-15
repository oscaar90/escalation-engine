"""Pydantic models for escalation policies, contacts, and incidents."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Contact(BaseModel):
    name: str
    role: Literal["primary", "secondary", "manager"]
    channels: dict[str, str]


class Team(BaseModel):
    id: str
    name: str
    contacts: list[Contact]


class Service(BaseModel):
    id: str
    name: str
    tier: Literal["P1", "P2", "P3"]
    owner_team: str
    escalation_chain: list[str]
    sla_minutes: int = Field(gt=0)


class EscalationStep(BaseModel):
    level: int
    team: Team
    contact: Contact
    channel: str
    sla_remaining: int


class EscalationResult(BaseModel):
    service: Service
    chain: list[EscalationStep]
    timestamp: str
    query: str


class Policies(BaseModel):
    default_sla_minutes: int = 30
    escalation_timeout_minutes: int = 10
    fallback_team: str = "sre-oncall"
    audit: dict[str, str | bool]


class ServicesRegistry(BaseModel):
    services: list[Service]


class TeamsRegistry(BaseModel):
    teams: list[Team]


class PoliciesRegistry(BaseModel):
    policies: Policies
