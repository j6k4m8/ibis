import { browser } from '$app/environment';
import { get, writable } from 'svelte/store';

import * as api from '$lib/api';
import type { AuthResponse, User } from '$lib/types';

const TOKEN_KEY = 'ibis_token';

export type AuthState = {
  token: string | null;
  user: User | null;
  ready: boolean;
};

const initialState: AuthState = {
  token: null,
  user: null,
  ready: false,
};

const store = writable<AuthState>(initialState);
let initialized = false;

function persistToken(token: string | null) {
  if (!browser) {
    return;
  }

  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function setAuth(response: AuthResponse) {
  persistToken(response.access_token);
  store.set({ token: response.access_token, user: response.user, ready: true });
}

async function init(): Promise<AuthState> {
  if (initialized) {
    return get(store);
  }
  initialized = true;

  if (!browser) {
    const state = { ...initialState, ready: true };
    store.set(state);
    return state;
  }

  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    const state = { ...initialState, ready: true };
    store.set(state);
    return state;
  }

  try {
    const user = await api.me(token);
    const state = { token, user, ready: true };
    store.set(state);
    return state;
  } catch {
    clear();
    return { ...initialState, ready: true };
  }
}

async function login(email: string, password: string): Promise<AuthState> {
  const response = await api.login(email, password);
  setAuth(response);
  return get(store);
}

async function register(email: string, password: string, displayName?: string): Promise<AuthState> {
  const response = await api.register(email, password, displayName);
  setAuth(response);
  return get(store);
}

function clear() {
  persistToken(null);
  store.set({ ...initialState, ready: true });
}

export const authStore = {
  subscribe: store.subscribe,
  init,
  login,
  register,
  clear,
};
