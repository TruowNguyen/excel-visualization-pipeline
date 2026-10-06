/** Small, decorative UI icons; accessible names stay on the controls. */
const paths: Record<string, string> = {
  overview: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M9 9h12"/>',
  statistics: '<path d="M3 3v18h18M7 16v-5m5 5V7m5 9v-3"/>',
  comparison: '<path d="M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4"/>',
  audit: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  import: '<path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/>',
  history: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  report: '<path d="M14 3H5v18h14V8zM14 3v5h5M8 12h8M8 16h5"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-2l2 2M4 17l2 2a7 7 0 0 0 12-2"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/>',
};

export function uiIcon(name: string): string {
  return `<svg class="ui-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths[name] || paths.overview}</svg>`;
}
