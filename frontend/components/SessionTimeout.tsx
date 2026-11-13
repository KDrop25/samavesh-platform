"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { extendSession, logout } from "@/app/actions";
import { SESSION_EXP_COOKIE } from "@/lib/cookie-options";

const WARN_MS = 2 * 60 * 1000;

/**
 * WCAG 2.2.1 (Timing Adjustable): warn before the 30-minute idle timeout and let the user
 * extend it with one action. Opening a modal <dialog> moves focus into it, so the warning
 * is announced to screen-reader users without a live region.
 */
export function SessionTimeout({ labels }: { labels: { title: string; body: string; stay: string; signOut: string } }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const router = useRouter();

  useEffect(() => {
    const tick = () => {
      const match = document.cookie.match(new RegExp(`(?:^|; )${SESSION_EXP_COOKIE}=(\\d+)`));
      const left = match ? Number(match[1]) - Date.now() : 0;
      if (left <= 0) {
        dialog.current?.close();
        router.push("/login?timeout=1");
      } else if (left < WARN_MS && !dialog.current?.open) dialog.current?.showModal();
    };
    const id = setInterval(tick, 10_000);
    return () => clearInterval(id);
  }, [router]);

  return (
    <dialog
      ref={dialog}
      aria-labelledby="timeout-title"
      className="m-auto max-w-md rounded-lg border-2 border-border bg-bg p-6 text-fg"
    >
      <h2 id="timeout-title">{labels.title}</h2>
      <p className="mb-5">{labels.body}</p>
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="btn"
          autoFocus
          onClick={async () => {
            await extendSession();
            dialog.current?.close();
          }}
        >
          {labels.stay}
        </button>
        <form action={logout}>
          <button type="submit" className="btn btn-secondary">
            {labels.signOut}
          </button>
        </form>
      </div>
    </dialog>
  );
}
