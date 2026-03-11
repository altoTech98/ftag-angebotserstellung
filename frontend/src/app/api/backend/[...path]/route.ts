import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
const PYTHON_SERVICE_KEY = process.env.PYTHON_SERVICE_KEY || '';

const DEFAULT_TIMEOUT_MS = 30_000;
const LONG_TIMEOUT_MS = 300_000;
const LONG_TIMEOUT_PATHS = ['/api/analyze', '/api/analyze/project'];

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxyToPython(request: Request, ctx: RouteContext): Promise<Response> {
  // Verify session
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json(
      { error: 'Nicht authentifiziert' },
      { status: 401 }
    );
  }

  // Build target URL: /api/backend/X/Y -> /api/X/Y
  const pathSegments = await ctx.params;
  const targetPath = `/api/${pathSegments.path.join('/')}`;
  const url = new URL(request.url);
  const queryString = url.search; // includes leading '?'
  const targetUrl = `${PYTHON_BACKEND_URL}${targetPath}${queryString}`;

  // Determine timeout
  const timeoutMs = LONG_TIMEOUT_PATHS.some((p) => targetPath.startsWith(p))
    ? LONG_TIMEOUT_MS
    : DEFAULT_TIMEOUT_MS;

  // Build headers
  const forwardedHeaders: Record<string, string> = {
    'X-Service-Key': PYTHON_SERVICE_KEY,
    'X-User-Id': session.user.id,
    'X-User-Role': (session.user as { role?: string }).role || 'viewer',
    'X-User-Email': session.user.email,
  };

  const contentType = request.headers.get('Content-Type');
  if (contentType) {
    forwardedHeaders['Content-Type'] = contentType;
  }

  // AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    // Forward body for non-GET/HEAD methods
    const hasBody = !['GET', 'HEAD'].includes(request.method);
    const body = hasBody ? await request.arrayBuffer() : undefined;

    const response = await fetch(targetUrl, {
      method: request.method,
      headers: forwardedHeaders,
      body,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Pass through Python response as-is
    const responseHeaders = new Headers();
    const responseContentType = response.headers.get('Content-Type');
    if (responseContentType) {
      responseHeaders.set('Content-Type', responseContentType);
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof DOMException && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Backend-Zeitueberschreitung' },
        { status: 504 }
      );
    }

    return NextResponse.json(
      { error: 'Backend nicht erreichbar' },
      { status: 502 }
    );
  }
}

export async function GET(request: Request, ctx: RouteContext) {
  return proxyToPython(request, ctx);
}

export async function POST(request: Request, ctx: RouteContext) {
  return proxyToPython(request, ctx);
}

export async function PUT(request: Request, ctx: RouteContext) {
  return proxyToPython(request, ctx);
}

export async function DELETE(request: Request, ctx: RouteContext) {
  return proxyToPython(request, ctx);
}

export async function PATCH(request: Request, ctx: RouteContext) {
  return proxyToPython(request, ctx);
}
