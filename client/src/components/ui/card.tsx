import React from 'react';

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

export type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  title?: string;
  subtitle?: string;
};

export function Card({ title, subtitle, className = '', children, ...props }: CardProps) {
  return (
    <div
      className={cx('rounded-2xl border border-border bg-card p-6 shadow-lg', 'backdrop-blur-sm', className)}
      {...props}
    >
      {(title || subtitle) && (
        <div className="mb-6">
          {title && <h3 className="text-xl font-semibold text-foreground">{title}</h3>}
          {subtitle && <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  );
}

