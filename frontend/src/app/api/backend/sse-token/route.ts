import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { createHmac } from 'crypto';

const TOKEN_EXPIRY_SECONDS = 600; // 10 minutes

function base64urlEncode(data: string | Buffer): string {
  const buf = typeof data === 'string' ? Buffer.from(data) : data;
  return buf.toString('base64url');
}

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
  const payloadB64 = base64urlEncode(payloadStr);

  const hmac = createHmac('sha256', secret);
  hmac.update(payloadStr);
  const signatureB64 = base64urlEncode(hmac.digest());

  const token = `${payloadB64}.${signatureB64}`;

  return NextResponse.json({
    token,
    expires_in: TOKEN_EXPIRY_SECONDS,
  });
}
