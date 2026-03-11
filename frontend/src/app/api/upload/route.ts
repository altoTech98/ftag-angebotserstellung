import { handleUpload, type HandleUploadBody } from '@vercel/blob/client';
import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';

export async function POST(request: Request): Promise<NextResponse> {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json(
      { error: 'Nicht authentifiziert' },
      { status: 401 },
    );
  }

  const body = (await request.json()) as HandleUploadBody;

  const jsonResponse = await handleUpload({
    body,
    request,
    onBeforeGenerateToken: async () => {
      return {
        allowedContentTypes: [
          'application/pdf',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ],
        addRandomSuffix: true,
        tokenPayload: JSON.stringify({
          userId: session.user.id,
        }),
      };
    },
    onUploadCompleted: async () => {
      // Not reliable locally (requires public URL for webhook)
      // File metadata is saved client-side via saveFileMetadata server action
    },
  });

  return NextResponse.json(jsonResponse);
}
