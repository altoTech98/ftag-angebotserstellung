'use server';

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
const PYTHON_SERVICE_KEY = process.env.PYTHON_SERVICE_KEY || '';

/**
 * Downloads files from Vercel Blob and uploads them to Python's project_cache.
 * This bridges the gap between Vercel Blob storage and Python's in-memory cache.
 */
export async function prepareFilesForPython(
  projectId: string,
  fileIds: string[]
): Promise<{ success: true } | { error: string }> {
  try {
    const session = await auth.api.getSession({ headers: await headers() });
    if (!session) return { error: 'Nicht authentifiziert' };

    // Fetch file records from Prisma
    const files = await prisma.file.findMany({
      where: { id: { in: fileIds }, projectId },
    });

    if (files.length === 0) {
      return { error: 'Keine Dateien gefunden' };
    }

    // Download each file from Vercel Blob and build FormData
    const formData = new FormData();
    formData.append('project_id', projectId);

    for (const file of files) {
      const response = await fetch(file.downloadUrl);
      if (!response.ok) {
        return { error: `Datei ${file.name} konnte nicht heruntergeladen werden` };
      }
      const buffer = await response.arrayBuffer();
      const blob = new Blob([buffer], { type: file.contentType });
      formData.append('files', blob, file.name);
    }

    // POST to Python upload endpoint to populate project_cache
    const uploadResponse = await fetch(
      `${PYTHON_BACKEND_URL}/api/upload/project`,
      {
        method: 'POST',
        headers: {
          'X-API-Key': PYTHON_SERVICE_KEY,
        },
        body: formData,
      }
    );

    if (!uploadResponse.ok) {
      const errorText = await uploadResponse.text();
      return { error: `Python-Upload fehlgeschlagen: ${errorText}` };
    }

    return { success: true };
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'Unbekannter Fehler' };
  }
}

/**
 * Creates an Analysis record in Prisma with status "running".
 */
export async function createAnalysis(
  projectId: string
): Promise<{ analysisId: string } | { error: string }> {
  try {
    const session = await auth.api.getSession({ headers: await headers() });
    if (!session) return { error: 'Nicht authentifiziert' };

    // Permission check
    const hasPermission = await auth.api.userHasPermission({
      body: {
        userId: session.user.id,
        permissions: { analysis: ['create'] },
      },
    });
    if (!hasPermission?.success) {
      return { error: 'Keine Berechtigung fuer Analyse' };
    }

    const analysis = await prisma.analysis.create({
      data: {
        projectId,
        status: 'running',
        startedAt: new Date(),
        startedBy: session.user.id,
      },
    });

    return { analysisId: analysis.id };
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'Unbekannter Fehler' };
  }
}

/**
 * Saves the analysis result to Prisma, marking it as completed.
 */
export async function saveAnalysisResult(
  analysisId: string,
  result: unknown
): Promise<{ success: true } | { error: string }> {
  try {
    const session = await auth.api.getSession({ headers: await headers() });
    if (!session) return { error: 'Nicht authentifiziert' };

    const analysis = await prisma.analysis.findUnique({
      where: { id: analysisId },
    });
    if (!analysis) return { error: 'Analyse nicht gefunden' };

    await prisma.analysis.update({
      where: { id: analysisId },
      data: {
        status: 'completed',
        result: result as Record<string, unknown>,
        endedAt: new Date(),
      },
    });

    revalidatePath(`/projekte/${analysis.projectId}`);
    return { success: true };
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'Unbekannter Fehler' };
  }
}
