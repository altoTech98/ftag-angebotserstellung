import { NextResponse } from 'next/server';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
const HEALTH_TIMEOUT_MS = 5_000;

export async function GET() {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);

  try {
    const response = await fetch(`${PYTHON_BACKEND_URL}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const data = await response.json();
    return NextResponse.json({
      status: 'connected',
      python: data,
    });
  } catch {
    clearTimeout(timeoutId);
    return NextResponse.json(
      { status: 'disconnected' },
      { status: 503 }
    );
  }
}
