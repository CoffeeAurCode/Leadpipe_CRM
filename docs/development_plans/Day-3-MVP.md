# Day 3 MVP Assumptions (Frozen)

**Last Updated:** 2026-01-27  
**Status:** LOCKED - Do not modify scope beyond what is documented here

---

## 🔒 Day 3 MVP Assumptions (Frozen)

### 1️⃣ Vapi Responsibilities (OUTSIDE Backend)

Vapi is assumed to **fully handle**:
- Call pickup
- Speech-to-text (STT)
- Transcript generation

**Backend will NEVER deal with:**
- Audio streaming
- Whisper integration
- Call state management
- Partial transcripts
- Real-time audio processing

**Critical Contract:** Backend receives **final transcript text only** as a string.

---

### 2️⃣ Backend Responsibilities

Backend is responsible **ONLY** for:
- Receiving a single full transcript (string input)
- Running AI extraction to produce complaint JSON
- Creating a complaint record in the database
- Storing complaint data via existing ORM models

**Out of Scope:**
- No UI
- No dashboards
- No analytics
- No call handling
- No audio processing

---

### 3️⃣ Call Constraints (ABSOLUTELY FIXED)

- **Single caller only**
- **English language only**
- **No interruptions**
- **No follow-up questions**
- **No callbacks**
- **No multi-turn conversation recovery**

**Workflow:** One transcript → one complaint → end.

---

## 🧱 Engineering Rules (Strictly Enforced)

1. **Do NOT suggest improvements** beyond Day 3 scope
2. **Do NOT add future-proofing** features
3. **Do NOT introduce** async workflows, queues, or retry mechanisms
4. **Do NOT redesign schemas** already in place
5. **Treat this as a throwaway MVP slice**, not a production system

---

## 📌 Scope Lock Statement

> **"If a feature is not listed here, it is out of scope for Day 3."**

This document serves as the single source of truth for Day 3 MVP boundaries. Any work that deviates from these assumptions must be explicitly discussed and approved before implementation.

---

## ✅ What This Means in Practice

### ✅ In Scope
- Text-based AI extraction endpoint
- Database storage of extracted complaints
- Integration with existing SQLAlchemy models
- Basic error handling for extraction failures

### ❌ Out of Scope
- Audio handling
- Multi-language support
- Complex conversation flows
- Real-time processing
- Admin dashboards
- Reporting features
- User notifications
- Callback systems
- Queue/worker architecture
