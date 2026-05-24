# Implementation Plan — Changes from Chnages_needed.md

> Scope: three independent changes. Each section lists exact files, steps, and risks.
> Execute in the order below — Change 3 (buttons) first since it has zero risk, Change 2 next, Change 1 last (largest blast radius).

---

## Change 3 — Move Action Buttons (Lowest risk, do first)

**What:** Remove the fixed floating action buttons (FABs) from bottom-left and replace them with an inline action bar placed **below** the tab switcher row. Same contextual logic (which buttons appear) is preserved.

### Files to touch
| File | Change |
|---|---|
| `frontend/src/components/PropertiesPage.jsx` | Remove FAB block, add inline action bar |

### Current button locations in the code
- **Top-level view** (`line ~686`): fixed div at `bottom-8 left-8` with 4 FABs
- **Property drill-down** (`line ~570`): single FAB for "Add Building"
- **Building drill-down** (`line ~498`): single FAB for "Add Unit"

### Implementation steps

1. **Top-level view** — delete the `<div data-tour="fab-buttons" className="fixed bottom-8 left-8 ...">` block and replace with an action bar between the ViewSwitcher row and the `<AnimatePresence>` block:
   ```jsx
   {/* Action bar */}
   <div className="flex items-center gap-2 flex-wrap">
     {viewMode === 'properties' && (
       <button onClick={() => setShowAddProperty(true)} className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors">
         <Layers className="w-4 h-4" /> Add Property
       </button>
     )}
     {viewMode === 'buildings' && (
       <button onClick={() => setShowAddBuilding(true)} className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors">
         <Building2 className="w-4 h-4" /> Add Building
       </button>
     )}
     <button onClick={() => setShowAddUnit(true)} className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border bg-secondary text-foreground text-sm font-medium hover:bg-secondary/80 transition-colors">
       <Plus className="w-4 h-4" /> Add Unit
     </button>
     <button onClick={() => setShowCsvImport(true)} className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border bg-secondary text-foreground text-sm font-medium hover:bg-secondary/80 transition-colors">
       <Upload className="w-4 h-4" /> Import CSV
     </button>
   </div>
   ```

2. **Property drill-down** — replace `<FAB icon={Building2} label="Add Building" .../>` with an inline button placed in the header row (next to the Delete button):
   ```jsx
   <button onClick={() => setShowAddBuilding(true)} className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors flex-shrink-0">
     <Building2 className="w-4 h-4" /> Add Building
   </button>
   ```

3. **Building drill-down** — same pattern: replace `<FAB icon={Plus} label="Add Unit" .../>` with an inline button in the header row.

4. If `FAB` component is only used in `PropertiesPage.jsx`, remove it from the file. If used elsewhere, keep it.

### Risk
- No backend changes. Pure layout shift. Onboarding tour targets `data-tour="fab-buttons"` — after the move, update the selector in `frontend/src/config/onboardingTours.js` to point to the new action bar's `data-tour` attribute.

---

## Change 2 — Unit Address Auto-Fill + VAPI Address Search

### Part A — Frontend: Address field in AddPropertyModal

**Files to touch**
| File | Change |
|---|---|
| `frontend/src/components/AddPropertyModal.jsx` | Label rename + auto-fill logic |
| `frontend/src/services/apiService.js` | Add `fetchBuildingById` helper (if not already there) |

**Steps**

1. **Rename label** — change `"Building Address"` → `"Address"` (line ~171 in `AddPropertyModal.jsx`).

2. **Auto-fill for building-linked units** — when `initialBuildingId` is not null, on modal open fetch the building details and its parent property:
   ```js
   // on mount when initialBuildingId is set
   useEffect(() => {
     if (!initialBuildingId) return;
     (async () => {
       const building = await fetchBuildingById(initialBuildingId);  // GET /buildings/{id}
       const property = building.property_id
         ? await fetchPropertyGroupById(building.property_id)         // GET /property-groups/{id} or from cache
         : null;
       const parts = [
         building.name,
         building.address,
         property?.name,
         property?.address,
       ].filter(Boolean);
       setFormData(prev => ({ ...prev, address: parts.join(', ') }));
       setAddressAutoFilled(true);
     })();
   }, [initialBuildingId]);
   ```

3. **Visual cue** — when `addressAutoFilled` is true, show a subtle helper text below the field:
   > "Auto-filled from building info — you can edit this"

4. **For independent units** — `initialBuildingId` is null, field stays blank and fully editable (no change to current behaviour).

5. **`apiService.js`** — add:
   - `fetchBuildingById(id)` → `GET /buildings/{id}` (backend route already exists)
   - `fetchPropertyGroupById(id)` → `GET /property-groups/{id}` — check if this route exists; if not, fetch all groups and find by id from the cached list, or add the route to the backend.

   > **Check first:** `GET /property-groups/{id}` is NOT listed in the current routes. Either add it to `backend/app/routes/property_groups.py`, or in the frontend resolve the property by filtering from the already-loaded `propertyGroups` list (pass it as a prop to `AddPropertyModal`).

   **Recommended approach (no new backend route):** Pass the `propertyGroups` array as a prop from `PropertiesPage` into `AddPropertyModal`. Then in the modal, resolve the property from that array using `building.property_id`.

### Part B — VAPI lease agent: address-based search

**Files to touch**
| File | Change |
|---|---|
| `backend/app/routes/leasing.py` | Add address filter to `find_listing` and `search` endpoints |
| `backend/app/services/vapi_agent_config.py` | Update tool descriptions to mention address search |

**Steps**

1. **`GET /leasing/find-listing`** — current query searches by `flat_number` or `title`. Extend it to also search by `flats.address`:
   ```python
   # In find_listing handler, after existing flat_number / title search fails,
   # try an address-based search via a join:
   result = svc.table("lease_listings") \
       .select("*, flats!inner(address)") \
       .ilike("flats.address", f"%{query}%") \
       .eq("is_active", True) \
       .execute()
   ```
   Return the same `{found, listing_uuid, address, bedrooms, ...}` shape.

2. **`GET /leasing/search`** — add an optional `address: Optional[str] = None` query param. When provided, post-filter the fetched listings to those whose linked flat address contains the string (case-insensitive). The `flats.address` value is already available if we select it in the query.

3. **`vapi_agent_config.py` — `find_listing` tool** — update the `description` field to mention:
   > "Query can be a flat number, listing title, or part of the unit's address (street name, building name, etc.)"

4. **`vapi_agent_config.py` — `search_available_listings` tool** — add `address` as an optional string parameter in the tool's input schema, and update the description:
   > "Optional: pass a partial address string to filter listings to a specific location."

5. **Update agent system prompt** in `build_lease_config` to instruct the agent:
   > "If the caller mentions a street, neighbourhood, or building name, pass it as the `address` parameter when calling `search_available_listings` or `find_listing`."

6. Run `python backend/scripts/update_lease_agents.py` after changes to push the updated agent config to all active per-manager VAPI assistants.

### Risk
- The `flats` join in PostgREST with `!inner` on `lease_listings` may not work if `flat_uuid` is nullable on some listings. Test with `LEFT JOIN` (no `!inner`) and filter in Python if needed.
- Address search is additive — existing `find_listing` logic (flat number / title) runs first; address is a fallback. No existing functionality removed.

---

## Change 1 — Bilingual UI (English + Quebec French) (Largest scope, do last)

**Library:** `react-i18next` + `i18next` (industry standard, tree-shakeable, works with React 18)

**Files to touch**
| File | Change |
|---|---|
| `frontend/package.json` | Add `i18next`, `react-i18next` |
| `frontend/src/main.jsx` | Import i18n config before app renders |
| `frontend/src/i18n/index.js` | NEW — i18next init |
| `frontend/src/i18n/en.json` | NEW — English strings |
| `frontend/src/i18n/fr-CA.json` | NEW — Quebec French strings |
| `frontend/src/components/TopBar.jsx` | Add EN/FR toggle button |
| All ~67 `.jsx` components | Wrap hardcoded strings with `t()` |

### Implementation steps

#### Step 1 — Install packages
```bash
cd frontend && npm install i18next react-i18next
```

#### Step 2 — Create i18n config (`frontend/src/i18n/index.js`)
```js
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './en.json';
import frCA from './fr-CA.json';

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, 'fr-CA': { translation: frCA } },
  lng: localStorage.getItem('lang') || 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export default i18n;
```

#### Step 3 — Create translation files

**`en.json`** — extract ALL hardcoded strings from all components. Organise by namespace:
```json
{
  "nav": { "dashboard": "Dashboard", "properties": "Properties", ... },
  "topbar": { "welcome": "Welcome back!", "refresh": "Refresh" },
  "properties": { "addProperty": "Add Property", "addBuilding": "Add Building", "addUnit": "Add Unit", "importCsv": "Import CSV", ... },
  "complaints": { ... },
  "tenants": { ... },
  "modals": { "cancel": "Cancel", "save": "Save", "delete": "Delete", ... },
  "errors": { ... },
  ...
}
```

**`fr-CA.json`** — Quebec French translations for every key. Use formal "vous" register matching Canadian government French standards. Key examples:
```json
{
  "nav": { "dashboard": "Tableau de bord", "properties": "Propriétés", ... },
  "topbar": { "welcome": "Bienvenue!", "refresh": "Actualiser" },
  "properties": { "addProperty": "Ajouter une propriété", "addBuilding": "Ajouter un bâtiment", "addUnit": "Ajouter une unité", "importCsv": "Importer CSV", ... },
  ...
}
```

#### Step 4 — Wire i18n into app (`frontend/src/main.jsx`)
```js
import './i18n';  // must be before App import
import App from './App';
```

#### Step 5 — Add language toggle to `TopBar.jsx`
```jsx
import { useTranslation } from 'react-i18next';

function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = i18n.language;
  const toggle = () => {
    const next = current === 'en' ? 'fr-CA' : 'en';
    i18n.changeLanguage(next);
    localStorage.setItem('lang', next);
  };
  return (
    <button onClick={toggle} className="px-3 py-1.5 rounded-lg border border-border text-sm font-medium hover:bg-secondary transition-colors">
      {current === 'en' ? 'FR' : 'EN'}
    </button>
  );
}
```
Add `<LanguageToggle />` inside `TopBar`'s button row (between ThemeToggle and Refresh button).

#### Step 6 — Update all components

For each component file, apply this pattern:
```jsx
// Before
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();
  return <button>{t('properties.addUnit')}</button>;
}
```

**Priority order for components** (tackle pages before modals, modals before small cards):
1. `Sidebar.jsx` — nav labels
2. `TopBar.jsx` — welcome text
3. `PropertiesPage.jsx` — all button labels, empty state text
4. `TenantManagement.jsx`
5. `ComplaintsPage.jsx`
6. `LeasingTab.jsx`
7. `Dashboard.jsx`, `BentoDashboard.jsx`
8. All modal files (AddPropertyGroupModal, AddBuildingModal, AddPropertyModal, etc.)
9. `SettingsPage.jsx`
10. Remaining small components (cards, badges, chart labels)

**Handle dynamic/interpolated strings:**
```jsx
// Count interpolation
t('properties.unitCount', { count: allUnits.length })
// en.json: "unitCount": "{{count}} unit" + pluralisation key "unitCount_other": "{{count}} units"
// fr-CA.json: "unitCount": "{{count}} unité", "unitCount_other": "{{count}} unités"
```

**Do NOT translate:**
- Data values from the database (tenant names, property names, etc.)
- Error codes / raw API error messages (translate the label, not the raw error)
- VAPI/Twilio/Stripe third-party strings

#### Step 7 — Verification checklist
- [ ] Toggle switches language instantly without page reload
- [ ] Language persists across page refresh (via localStorage)
- [ ] All buttons, labels, placeholders, and error messages change
- [ ] Dynamic strings (plurals, counts) render correctly in both languages
- [ ] No existing functionality broken (forms still submit, modals still open)

### Risk
- **Largest risk** in this change set — touches every component. If any `t()` key is missing from the JSON, i18next falls back to the key string (visible to user as a raw key like `"properties.addUnit"`). Mitigation: extract strings to JSON file first, then replace in components — never replace before adding to both JSON files.
- Quebec French pluralization differs from standard French — use `i18next-intervalplural-postprocessor` or manually define plural forms in fr-CA.json for each count string.
- After full implementation, run the app in French mode and click through every page to catch any missed strings before shipping.

---

## Execution Order Summary

| Order | Change | Risk | Est. Files |
|---|---|---|---|
| 1st | Change 3 — Move buttons | Low | 2 |
| 2nd | Change 2 — Address auto-fill + VAPI search | Medium | 5–6 |
| 3rd | Change 1 — Bilingual i18n | High | ~75 |

Each change is independently testable and deployable. Commit after each one before starting the next.
