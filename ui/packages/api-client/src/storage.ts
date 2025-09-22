export interface TokenStorage {
  get(): string | null;
  set(token: string | null): void;
}

export function createBrowserTokenStorage(key: string): TokenStorage {
  return {
    get() {
      if (typeof window === "undefined") return null;
      return window.localStorage.getItem(key);
    },
    set(token) {
      if (typeof window === "undefined") return;
      if (token) window.localStorage.setItem(key, token);
      else window.localStorage.removeItem(key);
    },
  };
}

export function createMemoryTokenStorage(): TokenStorage {
  let value: string | null = null;
  return {
    get: () => value,
    set: (t) => { value = t; },
  };
}

