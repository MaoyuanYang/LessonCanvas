"use client";

import * as AlertDialogPrimitive from "@radix-ui/react-alert-dialog";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "quiet" | "destructive";

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-accent text-white hover:bg-accent/90 disabled:bg-stale/40",
  secondary: "border border-line bg-paper text-ink hover:bg-surface-alt disabled:text-stale",
  quiet: "text-accent hover:bg-surface-alt disabled:text-stale",
  destructive: "bg-severe text-white hover:bg-severe/90 disabled:bg-stale/40",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export function Button({ variant = "primary", className = "", ...rest }: ButtonProps) {
  return (
    <button
      className={`rounded px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus disabled:cursor-not-allowed ${variantClasses[variant]} ${className}`}
      {...rest}
    />
  );
}

interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
}

export function Modal({ open, onOpenChange, title, description, children }: ModalProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 bg-ink/40" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded border border-line bg-paper p-6 shadow-lg focus-visible:outline-2 focus-visible:outline-focus">
          <DialogPrimitive.Title className="text-lg font-semibold text-ink">
            {title}
          </DialogPrimitive.Title>
          {description ? (
            <DialogPrimitive.Description className="mt-1 text-sm text-ink-secondary">
              {description}
            </DialogPrimitive.Description>
          ) : null}
          <div className="mt-4">{children}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

interface ConfirmModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  destructive?: boolean;
  busy?: boolean;
  onConfirm: () => void;
}

export function ConfirmModal({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  destructive = false,
  busy = false,
  onConfirm,
}: ConfirmModalProps) {
  return (
    <AlertDialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialogPrimitive.Portal>
        <AlertDialogPrimitive.Overlay className="fixed inset-0 bg-ink/40" />
        <AlertDialogPrimitive.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded border border-line bg-paper p-6 shadow-lg focus-visible:outline-2 focus-visible:outline-focus">
          <AlertDialogPrimitive.Title className="text-lg font-semibold text-ink">
            {title}
          </AlertDialogPrimitive.Title>
          <AlertDialogPrimitive.Description className="mt-2 text-sm text-ink-secondary">
            {description}
          </AlertDialogPrimitive.Description>
          <div className="mt-5 flex justify-end gap-3">
            <AlertDialogPrimitive.Cancel asChild>
              <Button variant="secondary" disabled={busy}>
                取消
              </Button>
            </AlertDialogPrimitive.Cancel>
            <AlertDialogPrimitive.Action asChild>
              <Button
                variant={destructive ? "destructive" : "primary"}
                disabled={busy}
                onClick={onConfirm}
              >
                {busy ? "处理中…" : confirmLabel}
              </Button>
            </AlertDialogPrimitive.Action>
          </div>
        </AlertDialogPrimitive.Content>
      </AlertDialogPrimitive.Portal>
    </AlertDialogPrimitive.Root>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const labels: Record<string, { text: string; className: string }> = {
    active: { text: "进行中", className: "bg-evidence/10 text-evidence" },
    deleting: { text: "删除中", className: "bg-warning/10 text-warning" },
    delete_failed: { text: "删除未完成", className: "bg-warning/10 text-warning" },
  };
  const entry = labels[status] ?? { text: status, className: "bg-stale/10 text-stale" };
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${entry.className}`}
    >
      {entry.text}
    </span>
  );
}

export function EmptyState({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="rounded border border-dashed border-line bg-surface-alt/60 p-8 text-center">
      <p className="text-base font-medium text-ink">{title}</p>
      <p className="mt-1 text-sm text-ink-secondary">{hint}</p>
    </div>
  );
}

export function Alert({
  tone,
  children,
}: {
  tone: "error" | "warning" | "info";
  children: ReactNode;
}) {
  const tones = {
    error: "border-severe/40 bg-severe/5 text-severe",
    warning: "border-warning/40 bg-warning/5 text-warning",
    info: "border-line bg-surface-alt text-ink-secondary",
  } as const;
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`rounded border p-3 text-sm ${tones[tone]}`}
    >
      {children}
    </div>
  );
}

export function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div aria-hidden className="space-y-3">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="h-16 animate-pulse rounded border border-line bg-surface-alt" />
      ))}
    </div>
  );
}
