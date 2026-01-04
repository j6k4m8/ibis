import { browser } from '$app/environment';

const WELCOME_PREFIX = 'ibis_welcome_seen';

export function hasSeenWelcome(userId: string | undefined | null): boolean {
  if (!browser || !userId) {
    return false;
  }
  return localStorage.getItem(`${WELCOME_PREFIX}_${userId}`) === 'true';
}

export function markWelcomeSeen(userId: string | undefined | null) {
  if (!browser || !userId) {
    return;
  }
  localStorage.setItem(`${WELCOME_PREFIX}_${userId}`, 'true');
}
