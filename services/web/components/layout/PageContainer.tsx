import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
};

/**
 * Reusable page-level container.
 * Wraps main content with consistent padding and max-width behaviour.
 * All page components should use this as their outermost wrapper.
 */
export function PageContainer({ children, className = "" }: Props) {
  return (
    <div className={`w-full h-full flex flex-col gap-6 ${className}`}>
      {children}
    </div>
  );
}
