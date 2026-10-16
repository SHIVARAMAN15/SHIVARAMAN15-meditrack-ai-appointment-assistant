import React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export default function Toast({ toasts, onDismiss }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="toast-container" role="region" aria-label="Notifications">
      {toasts.map((toast) => {
        const isSuccess = toast.type === 'success';
        const isError = toast.type === 'error';

        return (
          <div
            key={toast.id}
            className={`toast toast-${toast.type || 'info'}`}
          >
            {isSuccess && <CheckCircle2 size={18} style={{ color: 'var(--success)' }} />}
            {isError && <AlertCircle size={18} style={{ color: 'var(--danger)' }} />}
            {!isSuccess && !isError && <Info size={18} style={{ color: 'var(--primary)' }} />}

            <div style={{ flex: 1 }}>
              {toast.title && (
                <div style={{ fontWeight: 600, color: 'var(--neutral-900)', fontSize: '0.85rem' }}>
                  {toast.title}
                </div>
              )}
              <div style={{ color: 'var(--neutral-700)', fontSize: '0.8rem' }}>
                {toast.message}
              </div>
            </div>

            <button
              type="button"
              className="modal-close-btn"
              onClick={() => onDismiss(toast.id)}
              style={{ padding: '2px' }}
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
