import React from 'react';

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export function Input({ className = '', ...props }: InputProps) {
  return (
    <input
      className={cx(
        'w-full rounded-lg border border-input bg-card px-4 py-2.5 text-sm',
        'placeholder:text-muted-foreground',
        'transition-all duration-200',
        'focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  );
}

