import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { createHmac } from 'crypto';

const TOKEN_EXPIRY_SECONDS = 600; // 10 minutes

export async function GET(_request: Request) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json(
      { error: 'Nicht authentifiziert' },
      { status: 401 }
    );
  }

  const secret = process.env.SSE_TOKEN_SECRET || process.env.PYTHON_SERVICE_KEY || '';
  const now = Math.floor(Date.now() / 1000);

  const payload = {
    sub: session.user.id,
    role: (session.user as { role?: string }).role || 'viewer',
    email: session.user.email,
    exp: now + TOKEN_EXPIRY_SECONDS,
    iat: now,
  };

  const payloadStr = JSON.stringify(payload);
  const payloadB64 = Buffer.from(payloadStr).toString('base64url');

  const signatureHex = createHmac('sha256', secret)
    .update(payloadStr)
    .digest('hex');

  const token = `${payloadB64}.${signatureHex}`;

  return NextResponse.json({
    token,
    expires_in: TOKEN_EXPIRY_SECONDS,
  });
}
