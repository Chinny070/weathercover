"use client";

import { useCallback, useRef, useState } from "react";
import type { TransactionHash } from "genlayer-js/types";
import { getTransaction, TransactionFinalityTimeoutError, waitForFinalizedTransaction, type AnyClient } from "@/lib/genlayer/contract";
import { phaseForTransaction, shouldRunSuccessfulSettlement, type TxPhase } from "@/lib/genlayer/txLifecycle";

/**
 * The transaction states this app must visibly distinguish:
 *   idle      -- nothing submitted yet
 *   submitted -- sent to the wallet, awaiting the visitor's signature
 *   pending   -- signed and broadcast, awaiting GenLayer consensus
 *   accepted  -- accepted by validators, still waiting for finality
 *   finalized -- actually FINALIZED and re-confirmed by re-reading the tx
 *   failed    -- rejected by the wallet, or consensus did not accept it
 */
export type { TxPhase };

export interface TxSnapshot {
  phase: TxPhase;
  hash: TransactionHash | null;
  statusName: string | null;
  resultName: string | null;
  error: string | null;
}

const INITIAL: TxSnapshot = { phase: "idle", hash: null, statusName: null, resultName: null, error: null };

/**
 * Wraps a single write call with the discipline every transaction in this
 * app must follow: never trust the write call's return value (a bare
 * transaction hash) as proof anything happened. Wait for a real status,
 * do not let ACCEPTED trigger final-state reads. `onSettled` runs only
 * after the transaction record confirms actual FINALIZED status.
 */
export function useTxAction(onSettled?: () => void) {
  const [snapshot, setSnapshot] = useState<TxSnapshot>(INITIAL);
  const inFlight = useRef(false);

  const run = useCallback(
    async (submit: (client: AnyClient) => Promise<TransactionHash>, client: AnyClient | null) => {
      if (inFlight.current) return;
      if (!client) {
        setSnapshot({ ...INITIAL, phase: "failed", error: "Connect a wallet first." });
        return;
      }
      inFlight.current = true;
      setSnapshot({ ...INITIAL, phase: "submitted" });
      let hash: TransactionHash;
      try {
        hash = await submit(client);
      } catch (e) {
        inFlight.current = false;
        setSnapshot({
          ...INITIAL,
          phase: "failed",
          error: e instanceof Error ? e.message : "Wallet rejected or failed to submit the transaction.",
        });
        return;
      }

      setSnapshot({ phase: "pending", hash, statusName: null, resultName: null, error: null });

      let finalizedSuccessfully = false;
      try {
        const tx = await waitForFinalizedTransaction(client, hash, {
          retries: 120,
          interval: 2000,
          onAccepted: (acceptedTx) => {
            setSnapshot({
              phase: "accepted",
              hash,
              statusName: acceptedTx.statusName ?? "ACCEPTED",
              resultName: acceptedTx.resultName ?? null,
              error: "Accepted — waiting for GenLayer finality…",
            });
          },
        });
        const statusName = tx.statusName ?? null;
        const resultName = tx.txExecutionResultName ?? tx.resultName ?? null;
        const phase = phaseForTransaction(statusName, tx.txExecutionResultName ?? null);
        setSnapshot({
          phase,
          hash,
          statusName,
          resultName,
          error: phase === "failed" ? `Transaction finalized unsuccessfully (${resultName ?? statusName ?? "unknown result"}).` : null,
        });
        inFlight.current = false;
        finalizedSuccessfully = shouldRunSuccessfulSettlement(statusName, tx.txExecutionResultName ?? null);
      } catch (e) {
        const tx = await getTransaction(hash, client).catch(() => null);
        const statusName = tx?.statusName ?? null;
        const resultName = tx?.txExecutionResultName ?? tx?.resultName ?? null;
        const phase = tx ? phaseForTransaction(statusName, tx.txExecutionResultName ?? null) : "failed";
        if (phase === "failed" || phase === "finalized") inFlight.current = false;
        setSnapshot({
          phase,
          hash,
          statusName,
          resultName,
          error: e instanceof Error ? e.message : "Could not confirm transaction finality.",
        });
        finalizedSuccessfully = Boolean(tx && shouldRunSuccessfulSettlement(statusName, tx.txExecutionResultName ?? null));
      }
      if (finalizedSuccessfully) onSettled?.();
    },
    [onSettled],
  );

  const reset = useCallback(() => {
    if (inFlight.current) return;
    setSnapshot(INITIAL);
  }, []);

  return { snapshot, run, reset };
}
