"use client";

import { useEffect, useRef, type ReactNode } from "react";

/**
 * Result message shown after a full page load (for example, coming back from a file upload).
 * It takes focus when it appears, so keyboard and screen-reader users land on the outcome
 * instead of at the top of the page.
 */
export function Notice({ error = false, children }: { error?: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => ref.current?.focus(), []);
  return (
    <div ref={ref} tabIndex={-1} role={error ? "alert" : "status"} className={error ? "notice notice-error" : "notice"}>
      {children}
    </div>
  );
}
