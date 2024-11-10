import { type NextRequest, NextResponse } from 'next/server';

import { env } from '~/env';

const defaultRoute = env.NEXT_PUBLIC_CONSUMER_MODE ? '/chat' : '/competitions';

function redirectUrlPath(path: string, request: NextRequest) {
  return new URL(
    `${path}${request.nextUrl.search}${request.nextUrl.hash}`,
    request.url,
  );
}

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname === '/') {
    return NextResponse.redirect(redirectUrlPath(defaultRoute, request));
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/:path*',
};
