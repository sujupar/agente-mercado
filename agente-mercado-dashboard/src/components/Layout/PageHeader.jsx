/**
 * PageHeader — cabecera consistente por página.
 * Muestra título, descripción opcional y área de acciones (botones, DateFilter, etc).
 */

export function PageHeader({ title, description, actions, onBack }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 pb-5 mb-6 border-b border-fm-border">
      <div className="min-w-0">
        {onBack && (
          <button
            onClick={onBack}
            className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-fm-text-dim hover:text-fm-primary transition-colors focus-ring rounded"
          >
            ← Volver
          </button>
        )}
        <h1 className="text-2xl font-semibold text-fm-text truncate">{title}</h1>
        {description && (
          <p className="text-sm text-fm-text-2 mt-1">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}
