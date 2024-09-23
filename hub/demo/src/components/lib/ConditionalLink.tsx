import Link from 'next/link';
import { type ComponentProps, forwardRef, type ReactNode } from 'react';

type Props = Omit<ComponentProps<'a'>, 'children' | 'href'> & {
  children: ReactNode;
  href: string | undefined | null;
  target?: ComponentProps<'a'>['target'];
};

export const ConditionalLink = forwardRef<HTMLAnchorElement, Props>(
  ({ href, ...props }, ref) => {
    if (!href) return props.children;
    return <Link href={href} {...props} ref={ref} />;
  },
);

ConditionalLink.displayName = 'ConditionalLink';
