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
];

/** Map section → the view name used by onNavigate() */
export const SECTION_VIEW = {
  dashboard: 'dashboard',
  properties: 'properties',
  tenants: 'tenants',
  complaints: 'complaints',
  calendar: 'calendar',
  workflow: 'workflow',
};

/** Map section → checklist item IDs to mark complete */
export const SECTION_CHECKLIST_IDS = {
  dashboard: ['dashboard-tour'],
  properties: ['properties-tour'],
  tenants: ['tenants-tour'],
  complaints: ['complaints-tour'],
  calendar: ['calendar-tour'],
  workflow: ['workflow-tour'],
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
    disableBeacon: true,
    placement: 'right',
    section: 'dashboard',
  },
  {
    target: '[data-tour="kpi-cards"]',
    title: 'Key Metrics',
    content: 'These cards show your most important numbers at a glance — total complaints, pending items, in-progress tasks, and today\'s appointments.',
    disableBeacon: true,
    section: 'dashboard',
  },
  {
    target: '[data-tour="trends-charts"]',
    title: 'Trends & Status',
    content: 'Track complaint trends over time and see the current status breakdown.',
    disableBeacon: true,
    section: 'dashboard',
  },
  {
    target: '[data-tour="category-charts"]',
    title: 'Categories & Appointments',
    content: 'See which complaint categories are most common, and upcoming appointments by day.',
    disableBeacon: true,
    section: 'dashboard',
  },

  // ── Properties ──
  {
    target: '[data-tour="view-switcher"]',
    title: 'View Modes',
    content: 'Switch between Properties, Buildings, and Units views to navigate your portfolio at different levels.',
    disableBeacon: true,
    section: 'properties',
  },
  {
    target: '[data-tour="property-list"]',
    title: 'Your Properties',
    content: 'Each card represents a property group. Click a card to drill down into its buildings and units.',
    disableBeacon: true,
    section: 'properties',
  },
  {
    target: '[data-tour="fab-buttons"]',
    title: 'Quick Add',
    content: 'Use these floating buttons to quickly add new properties, buildings, or units.',
    disableBeacon: true,
    placement: 'top',
    section: 'properties',
  },

  // ── Tenants ──
  {
    target: '[data-tour="tenant-filters"]',
    title: 'Filter Tenants',
    content: 'Filter tenants by rent status or lease status to quickly find who you\'re looking for.',
    disableBeacon: true,
    section: 'tenants',
  },
  {
    target: '[data-tour="tenant-table"]',
    title: 'Tenant Directory',
    content: 'Your complete tenant list — names, flats, lease dates, and rent status. Click any row for full details.',
    disableBeacon: true,
    section: 'tenants',
  },

  // ── Complaints ──
  {
    target: '[data-tour="quick-filters"]',
    title: 'Quick Filters',
    content: 'Filter complaints by status or priority to focus on what matters most.',
    disableBeacon: true,
    section: 'complaints',
  },
  {
    target: '[data-tour="complaint-cards"]',
    title: 'Complaint Cards',
    content: 'Each card shows a complaint summary. Click a card to see full details and update the status.',
    disableBeacon: true,
    section: 'complaints',
  },

  // ── Calendar ──
  {
    target: '[data-tour="calendar-header"]',
    title: 'Calendar Navigation',
    content: 'Navigate between months or jump to today. Use the filters to narrow by property or event type.',
    disableBeacon: true,
    section: 'calendar',
  },
  {
    target: '[data-tour="calendar-grid"]',
    title: 'Your Schedule',
    content: 'The calendar shows appointments and deadlines. Click any day to see all events for that date.',
    disableBeacon: true,
    section: 'calendar',
  },

  // ── Workflow ──
  {
    target: '[data-tour="sms-composer"]',
    title: 'Compose & Preview',
    content: 'Write your SMS or load a saved template. Insert dynamic variables like {name} and {unit} — see a live preview on the right.',
    disableBeacon: true,
    section: 'workflow',
  },
  {
    target: '[data-tour="sms-recipients"]',
    title: 'Select Recipients',
    content: 'Pick which tenants receive the message. Use search and filters to narrow down, then check the boxes.',
    disableBeacon: true,
    section: 'workflow',
  },
];

/** Get the first step index for a given section */
export function getFirstStepIndex(sectionId) {
  return ALL_STEPS.findIndex((s) => s.section === sectionId);
}
