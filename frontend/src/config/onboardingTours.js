/**
 * Tour step definitions for the full CRM walkthrough.
 * Each step has a `section` field linking it to a view/checklist item.
 * The tour controller uses this to auto-navigate between pages.
 */

export const SECTION_ORDER = [
  'dashboard',
  'properties',
  'tenants',
  'complaints',
  'calendar',
  'workflow',
  'leasing',
  'voice-stats',
];

/** Map section → the view name used by onNavigate() */
export const SECTION_VIEW = {
  dashboard: 'dashboard',
  properties: 'properties',
  tenants: 'tenants',
  complaints: 'complaints',
  calendar: 'calendar',
  workflow: 'workflow',
  leasing: 'leasing',
  'voice-stats': 'voice-stats',
};

/** Map section → checklist item IDs to mark complete */
export const SECTION_CHECKLIST_IDS = {
  dashboard: ['dashboard-tour'],
  properties: ['properties-tour'],
  tenants: ['tenants-tour'],
  complaints: ['complaints-tour'],
  calendar: ['calendar-tour'],
  workflow: ['workflow-tour'],
  leasing: ['leasing-tour'],
  'voice-stats': ['voice-stats-tour'],
};

/**
 * All steps in order. The `section` field determines which page the step belongs to.
 * When the section changes between steps, the tour controller navigates automatically.
 */
export const ALL_STEPS = [
  // ── Dashboard ──
  {
    target: '[data-tour="sidebar-nav"]',
    title: 'Navigation',
    content: 'Use the sidebar to switch between sections — Dashboard, Properties, Tenants, Complaints, Calendar, and SMS Workflow.',
    skipBeacon: true,
    placement: 'right',
    section: 'dashboard',
  },
  {
    target: '[data-tour="kpi-cards"]',
    title: 'Key Metrics',
    content: 'These cards show your most important numbers at a glance — total complaints, pending items, in-progress tasks, and today\'s appointments.',
    skipBeacon: true,
    section: 'dashboard',
  },
  {
    target: '[data-tour="trends-charts"]',
    title: 'Trends & Status',
    content: 'Track complaint trends over time and see the current status breakdown.',
    skipBeacon: true,
    section: 'dashboard',
  },
  {
    target: '[data-tour="category-charts"]',
    title: 'Categories & Appointments',
    content: 'See which complaint categories are most common, and upcoming appointments by day.',
    skipBeacon: true,
    section: 'dashboard',
  },

  // ── Properties ──
  {
    target: '[data-tour="view-switcher"]',
    title: 'Your Portfolio Structure',
    content: 'Properties are organised in 3 levels: Property Group → Building → Unit. Use these tabs to navigate each level.',
    skipBeacon: true,
    section: 'properties',
  },
  {
    target: 'body',
    placement: 'center',
    title: 'Step 1 of 3 — Add Your First Property',
    content: "Let's set up your portfolio together. First, create a top-level property group — e.g. \"Sunrise Estate\". Click Open Form to get started.",
    skipBeacon: true,
    section: 'properties',
    isActionStep: true,
    action: 'add-property',
  },
  {
    target: 'body',
    placement: 'center',
    title: 'Step 2 of 3 — Add a Building',
    content: "Great! Now add a building inside your property — e.g. \"Tower A\". It will be automatically linked to the property you just created.",
    skipBeacon: true,
    section: 'properties',
    isActionStep: true,
    action: 'add-building',
  },
  {
    target: 'body',
    placement: 'center',
    title: 'Step 3 of 3 — Add a Unit & Tenant',
    content: 'Almost there! Add your first unit (e.g. "A101"). You can also assign a tenant right now by ticking "Assign Tenant" inside the form.',
    skipBeacon: true,
    section: 'properties',
    isActionStep: true,
    action: 'add-unit',
  },
  {
    target: '[data-tour="property-list"]',
    title: 'Your Properties',
    content: 'Your first property is live! Each card represents a property group. Click a card to drill down into its buildings and units.',
    skipBeacon: true,
    section: 'properties',
  },
  {
    target: '[data-tour="action-buttons"]',
    title: 'Quick Add',
    content: 'Use these buttons to add more properties, buildings, or units at any time.',
    skipBeacon: true,
    placement: 'bottom',
    section: 'properties',
  },

  // ── Tenants ──
  {
    target: '[data-tour="tenant-filters"]',
    title: 'Filter Tenants',
    content: 'Filter tenants by rent status or lease status to quickly find who you\'re looking for.',
    skipBeacon: true,
    section: 'tenants',
  },
  {
    target: '[data-tour="tenant-table"]',
    title: 'Tenant Directory',
    content: 'Your complete tenant list — names, flats, lease dates, and rent status. Click any row for full details.',
    skipBeacon: true,
    section: 'tenants',
  },

  // ── Complaints ──
  {
    target: '[data-tour="quick-filters"]',
    title: 'Quick Filters',
    content: 'Filter complaints by status or priority to focus on what matters most.',
    skipBeacon: true,
    section: 'complaints',
  },
  {
    target: '[data-tour="complaint-cards"]',
    title: 'Complaint Cards',
    content: 'Each card shows a complaint summary. Click a card to see full details and update the status.',
    skipBeacon: true,
    section: 'complaints',
  },

  // ── Calendar ──
  {
    target: '[data-tour="calendar-header"]',
    title: 'Calendar Navigation',
    content: 'Navigate between months or jump to today. Use the filters to narrow by property or event type.',
    skipBeacon: true,
    section: 'calendar',
  },
  {
    target: '[data-tour="calendar-grid"]',
    title: 'Your Schedule',
    content: 'The calendar shows appointments and deadlines. Click any day to see all events for that date.',
    skipBeacon: true,
    section: 'calendar',
  },

  // ── Workflow ──
  {
    target: '[data-tour="sms-composer"]',
    title: 'Compose & Preview',
    content: 'Write your SMS or load a saved template. Insert dynamic variables like {name} and {unit} — see a live preview on the right.',
    skipBeacon: true,
    section: 'workflow',
  },
  {
    target: '[data-tour="sms-recipients"]',
    title: 'Select Recipients',
    content: 'Pick which tenants receive the message. Use search and filters to narrow down, then check the boxes.',
    skipBeacon: true,
    section: 'workflow',
  },

  // ── Leasing ──
  {
    target: '[data-tour="leasing-phone"]',
    title: 'Lease Agent Phone Number',
    content: 'This is the number prospective tenants call to enquire about available units. Your AI lease agent answers, qualifies callers, and logs them as leads automatically.',
    skipBeacon: true,
    section: 'leasing',
  },
  {
    target: '[data-tour="leasing-metrics"]',
    title: 'Leasing Metrics',
    content: 'See total calls received, qualification rate, and average call duration — all calculated automatically from the lease agent\'s call logs.',
    skipBeacon: true,
    section: 'leasing',
  },
  {
    target: '[data-tour="leasing-listings"]',
    title: 'Available Listings',
    content: 'Add listings for vacant units here. The AI lease agent uses these to match callers with the right property — including rent, bedrooms, availability date, and custom rules.',
    skipBeacon: true,
    section: 'leasing',
  },
  {
    target: '[data-tour="leasing-leads"]',
    title: 'Lead Pipeline',
    content: 'Every caller captured by the lease agent appears here. Filter by listing or qualification status, update a lead\'s stage, and export to CSV for follow-up.',
    skipBeacon: true,
    section: 'leasing',
  },

  // ── Voice Stats ──
  {
    target: '[data-tour="voice-phone"]',
    title: 'Complaint Agent Number',
    content: 'This is the inbound number your tenants call to log maintenance complaints. The AI voice agent handles the conversation and creates complaint records automatically.',
    skipBeacon: true,
    section: 'voice-stats',
  },
  {
    target: '[data-tour="voice-stats-cards"]',
    title: 'Call Statistics',
    content: 'See how many calls came in, how many resulted in a resolved complaint, and how many were escalated — all filterable by the last 7, 30, or 90 days.',
    skipBeacon: true,
    section: 'voice-stats',
  },
  {
    target: '[data-tour="voice-stats-chart"]',
    title: 'Call Volume Trend',
    content: 'A day-by-day bar chart of inbound call activity. Spot busy periods and track complaint volume over time at a glance.',
    skipBeacon: true,
    section: 'voice-stats',
  },
  {
    target: '[data-tour="voice-stats-recent"]',
    title: 'Recent Calls',
    content: 'The latest calls in reverse chronological order. Click any row to expand the full AI-generated transcript from that call.',
    skipBeacon: true,
    section: 'voice-stats',
  },
];

/** Get the first step index for a given section */
export function getFirstStepIndex(sectionId) {
  return ALL_STEPS.findIndex((s) => s.section === sectionId);
}
