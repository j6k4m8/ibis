import { writable } from 'svelte/store';

const NAV_PINNED_KEY = 'ibis.navPinned';

export const navPinned = writable(false);

let initialized = false;

export function initPreferences() {
  if (initialized) {
    return;
  }
  initialized = true;
  if (typeof window === 'undefined') {
    return;
  }
  const stored = window.localStorage.getItem(NAV_PINNED_KEY);
  if (stored !== null) {
    navPinned.set(stored === 'true');
    return;
  }
  if (window.matchMedia?.('(hover: none)').matches) {
    navPinned.set(true);
  }
}

export function setNavPinned(value: boolean) {
  navPinned.set(value);
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(NAV_PINNED_KEY, value ? 'true' : 'false');
}
