"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

/** Navigation link that marks the current page for assistive technology and visually. */
export function NavLink({ href, children }: { href: string; children: ReactNode }) {
  const pathname = usePathname();
  const current = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      aria-current={current ? "page" : undefined}
      className="inline-flex min-h-11 items-center px-2 font-semibold text-fg aria-[current=page]:underline aria-[current=page]:decoration-4"
    >
      {children}
    </Link>
  );
}
