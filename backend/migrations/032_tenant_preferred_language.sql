-- 032: Per-tenant complaint-agent language preference.
-- Recorded the first time a tenant passes phone verification on a language-specific
-- complaint assistant (entry/EN assistants send language=en, FR assistant sends language=fr
-- on the Verify_phone_number tool URL). Once set it is never overwritten by calls —
-- future inbound calls are routed by /voice/inbound-router and outbound calls by
-- /voice/call/outbound directly to the assistant matching this value.
-- NULL = tenant has never chosen — they get the bilingual language gate.

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS preferred_language text
  CHECK (preferred_language IN ('en', 'fr'));

COMMENT ON COLUMN tenants.preferred_language IS
  'Complaint-agent language chosen on the tenant''s first verified call: en | fr. NULL = not chosen yet (caller gets the bilingual gate).';
