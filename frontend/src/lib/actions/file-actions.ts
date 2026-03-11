'use server';

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';
import { del } from '@vercel/blob';

export interface FileMetadataInput {
  name: string;
  blobUrl: string;
  downloadUrl: string;
  size: number;
  contentType: string;
  projectId: string;
}

export async function saveFileMetadata(input: FileMetadataInput) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const file = await prisma.file.create({
    data: {
      name: input.name,
      blobUrl: input.blobUrl,
      downloadUrl: input.downloadUrl,
      size: input.size,
      contentType: input.contentType,
      projectId: input.projectId,
      uploadedBy: session.user.id,
    },
  });

  revalidatePath(`/projekte/${input.projectId}`);
  return file;
}

export async function deleteFile(fileId: string) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const file = await prisma.file.findUnique({
    where: { id: fileId },
  });
  if (!file) throw new Error('Datei nicht gefunden');

  await del(file.blobUrl);

  await prisma.file.delete({
    where: { id: fileId },
  });

  revalidatePath(`/projekte/${file.projectId}`);
}
