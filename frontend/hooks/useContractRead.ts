"use client";

import { useEffect, useState } from "react";

type ReadState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "error"; data: null; error: string }
  | { status: "ready"; data: T; error: null };

/**
 * Fetches from the deployed Intelligent Contract directly in the browser
 * (via lib/genlayer/contract.ts's read-only client) -- no server, no API
 * route, no database of our own. Re-runs whenever `deps` changes. Pattern
 * verified against protocolcourt/frontend/hooks/useContractRead.ts, a
 * working StudioNet frontend already in this workspace.
 */
export function useContractRead<T>(fetcher: () => Promise<T>, deps: unknown[]): ReadState<T> {
  const [state, setState] = useState<ReadState<T>>({ status: "loading", data: null, error: null });
  const [lastDeps, setLastDeps] = useState(deps);

  if (deps.length !== lastDeps.length || deps.some((d, i) => d !== lastDeps[i])) {
    setLastDeps(deps);
    if (state.status !== "loading") {
      setState({ status: "loading", data: null, error: null });
    }
  }

  useEffect(() => {
    let cancelled = false;
    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: "ready", data, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            status: "error",
            data: null,
            error: err instanceof Error ? err.message : "Failed to read from the contract.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
