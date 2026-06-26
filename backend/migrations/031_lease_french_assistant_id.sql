-- 031_lease_french_assistant_id.sql
-- Per-manager dedicated French lease assistant id, for the French-handoff routing
-- (see docs/development_plans/PLAN_lease_agent_french_squad_routing_2026-06-26.md).
-- Additive and nullable — no effect on managers without a French assistant; required
-- only for the per-manager fleet rollout of provision_lease_french_handoff.py --all.

ALTER TABLE manager_vapi_config
  ADD COLUMN IF NOT EXISTS vapi_lease_french_assistant_id text;

COMMENT ON COLUMN manager_vapi_config.vapi_lease_french_assistant_id IS
  'VAPI assistant id of the dedicated French-only lease assistant (handoff target). Null = none provisioned.';
