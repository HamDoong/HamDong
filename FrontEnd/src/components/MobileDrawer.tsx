import { useEffect } from 'react';
import { Sidebar } from './Sidebar';

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function MobileDrawer({
  open,
  onClose,
}: MobileDrawerProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  return (
    <div
      className={[
        'fixed inset-0 z-50 lg:hidden',
        open ? 'pointer-events-auto' : 'pointer-events-none',
      ].join(' ')}
      aria-hidden={!open}
    >
      <button
        type="button"
        onClick={onClose}
        aria-label="بستن منو"
        className={[
          'absolute inset-0 bg-slate-950/40 backdrop-blur-[1px] transition-opacity duration-300',
          open ? 'opacity-100' : 'opacity-0',
        ].join(' ')}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label="منوی موبایل"
        className={[
          'absolute right-0 top-0 h-full w-[88vw] max-w-[360px] border-l border-border/90 bg-white shadow-[0_24px_60px_rgba(15,23,42,0.18)] transition-transform duration-300 ease-out',
          open ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
      >
        <Sidebar mobile onClose={onClose} />
      </div>
    </div>
  );
}