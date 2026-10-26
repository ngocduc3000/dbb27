"use client";

export function ConfirmButton({ message, children, className }: { message: string; children: React.ReactNode; className?: string }) {
  return (
    <button className={className} onClick={(e) => { if (!confirm(message)) e.preventDefault(); }}>
      {children}
    </button>
  );
}

export function PrintButton() {
  return <button type="button" className="sec" onClick={() => window.print()}>In hóa đơn</button>;
}
