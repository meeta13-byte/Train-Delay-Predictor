// Small fetch helpers + a hook with in-memory caching so pages switch instantly.

import { useCallback, useEffect, useRef, useState } from 'react';

const cache = new Map();

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new ApiError('Cannot reach the RailPulse server. Is `npm run dev` running?', 0);
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(body.error || `Request failed (${res.status})`, res.status);
  return body;
}

export const api = {
  get: (url) => request(url),
  post: (url, data) => request(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data ?? {}) }),
};

export function clearCache() {
  cache.clear();
}

/**
 * useApi(key, loader): runs loader() when key changes. Results are cached per key,
 * so returning to a page (or re-picking a filter) is instant.
 */
export function useApi(key, loader, { enabled = true } = {}) {
  const [state, setState] = useState(() => {
    const hit = key && cache.get(key);
    return { data: hit ?? null, error: null, loading: enabled && !hit };
  });
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const run = useCallback(
    async (force = false) => {
      if (!enabled || !key) return;
      if (!force && cache.has(key)) {
        setState({ data: cache.get(key), error: null, loading: false });
        return;
      }
      setState((s) => ({ data: force ? s.data : null, error: null, loading: true }));
      try {
        const data = await loaderRef.current();
        cache.set(key, data);
        setState({ data, error: null, loading: false });
      } catch (error) {
        setState({ data: null, error, loading: false });
      }
    },
    [key, enabled],
  );

  useEffect(() => {
    let alive = true;
    if (!enabled || !key) return undefined;
    if (cache.has(key)) {
      setState({ data: cache.get(key), error: null, loading: false });
      return undefined;
    }
    setState({ data: null, error: null, loading: true });
    loaderRef
      .current()
      .then((data) => {
        cache.set(key, data);
        if (alive) setState({ data, error: null, loading: false });
      })
      .catch((error) => alive && setState({ data: null, error, loading: false }));
    return () => {
      alive = false;
    };
  }, [key, enabled]);

  return { ...state, reload: () => run(true) };
}
