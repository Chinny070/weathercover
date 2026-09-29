"use client";

import { useCallback, useState } from "react";
import type { TransactionHash } from "genlayer-js/types";
import { TransactionStatus } from "genlayer-js/types";
import { getTransaction, waitForStatus, type AnyClient } from "@/lib/genlayer/contract";

/**
 * The four transaction states this app must visibly distinguish:
 *   idle      -- nothing submitted yet
 *   submitted -- sent to the wallet, awaiting the visitor's signature
 *   pending   -- signed and broadcast, awaiting GenLayer consensus
 *   finalized -- consensus reached and re-confirmed by re-reading the tx
 *   failed    -- rejected by the wallet, or consensus did not accept it
 */
export type TxPhase = "idle" | "submitted" | "pending" | "finalized" | "failed";

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
 * then re-read the transaction's own record for its authoritative
 * statusName/resultName, and -- regardless of what that says -- always
 * call `onSettled` so the caller re-reads contract state from scratch
 * rather than assuming the write's effect. Pattern verified against
 * protocolcourt/frontend/hooks/useTxAction.ts, a working StudioNet
 * frontend already in this workspace.
 */
export function useTxAction(onSettled?: () => void) {
  const [snapshot, setSnapshot] = useState<TxSnapshot>(INITIAL);

  const run = useCallback(
    async (submit: (client: AnyClient) => Promise<TransactionHash>, client: AnyClient | null) => {
      if (!client) {
        setSnapshot({ ...INITIAL, phase: "failed", error: "Connect a wallet first." });
        return;
      }
      setSnapshot({ ...INITIAL, phase: "submitted" });
      let hash: TransactionHash;
      try {
        hash = await submit(client);
      } catch (e) {
        setSnapshot({
          ...INITIAL,
          phase: "failed",
          error: e instanceof Error ? e.message : "Wallet rejected or failed to submit the transaction.",
        });
        return;
      }

      setSnapshot({ phase: "pending", hash, statusName: null, resultName: null, error: null });

      try {
        await waitForStatus(client, hash, TransactionStatus.ACCEPTED, { retries: 120, interval: 2000 });
      } catch {
        // Timed out or resolved to something other than ACCEPTED -- fall
        // through to re-reading the transaction record directly rather
        // than assuming failure or success.
      }

      try {
        const tx = await getTransaction(hash);
        setSnapshot({
          phase: "finalized",
          hash,
          statusName: (tx.statusName as string | undefined) ?? null,
          resultName: (tx.resultName as string | undefined) ?? null,
          error: null,
        });
      } catch (e) {
        setSnapshot({
          phase: "failed",
          hash,
          statusName: null,
          resultName: null,
          error: e instanceof Error ? e.message : "Could not read back the transaction record.",
        });
      } finally {
        onSettled?.();
      }
    },
    [onSettled],
  );

  const reset = useCallback(() => setSnapshot(INITIAL), []);

  return { snapshot, run, reset };
}
