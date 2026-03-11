'use server';

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';
import { del } from '@vercel/blob';

export async function createProject(formData: FormData) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { project: ['create'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  const deadlineStr = formData.get('deadline') as string | null;

  const project = await prisma.project.create({
    data: {
      name: formData.get('name') as string,
      customer: (formData.get('customer') as string) || null,
      deadline: deadlineStr ? new Date(deadlineStr) : null,
      description: (formData.get('description') as string) || null,
      ownerId: session.user.id,
    },
  });

  revalidatePath('/projekte');
  return project;
}

export async function archiveProject(projectId: string) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const project = await prisma.project.findUnique({
    where: { id: projectId },
  });
  if (!project) throw new Error('Projekt nicht gefunden');

  // Only owner or admin can archive
  if (project.ownerId !== session.user.id && session.user.role !== 'admin') {
    throw new Error('Keine Berechtigung');
  }

  const updated = await prisma.project.update({
    where: { id: projectId },
    data: { status: 'archived' },
  });

  revalidatePath('/projekte');
  return updated;
}

export async function deleteProject(projectId: string) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const project = await prisma.project.findUnique({
    where: { id: projectId },
  });
  if (!project) throw new Error('Projekt nicht gefunden');

  // Only owner or admin can delete
  if (project.ownerId !== session.user.id && session.user.role !== 'admin') {
    throw new Error('Keine Berechtigung');
  }

  // Clean up blob files before cascading delete
  const files = await prisma.file.findMany({
    where: { projectId },
    select: { blobUrl: true },
  });

  const blobUrls = files.map((f) => f.blobUrl);
  if (blobUrls.length > 0) {
    await del(blobUrls);
  }

  await prisma.project.delete({
    where: { id: projectId },
  });

  revalidatePath('/projekte');
}

export async function shareProject(
  projectId: string,
  email: string,
  role: string = 'viewer'
) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { project: ['share'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  const project = await prisma.project.findUnique({
    where: { id: projectId },
  });
  if (!project) throw new Error('Projekt nicht gefunden');

  // Only owner or admin can share
  if (project.ownerId !== session.user.id && session.user.role !== 'admin') {
    throw new Error('Keine Berechtigung');
  }

  // Look up target user by email
  const targetUser = await prisma.user.findUnique({ where: { email } });
  if (!targetUser) return { error: 'Benutzer nicht gefunden' };

  // Cannot share with self
  if (targetUser.id === session.user.id) {
    return { error: 'Kann nicht mit sich selbst teilen' };
  }

  // Check for existing share
  const existing = await prisma.projectShare.findUnique({
    where: { projectId_userId: { projectId, userId: targetUser.id } },
  });
  if (existing) return { error: 'Projekt bereits geteilt' };

  const share = await prisma.projectShare.create({
    data: { projectId, userId: targetUser.id, role },
  });

  revalidatePath(`/projekte/${projectId}`);
  return { success: true, share };
}

export async function removeShare(shareId: string) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const share = await prisma.projectShare.findUnique({
    where: { id: shareId },
    include: { project: { select: { ownerId: true } } },
  });
  if (!share) throw new Error('Freigabe nicht gefunden');

  // Only project owner or admin can remove shares
  if (share.project.ownerId !== session.user.id && session.user.role !== 'admin') {
    throw new Error('Keine Berechtigung');
  }

  await prisma.projectShare.delete({ where: { id: shareId } });
  revalidatePath(`/projekte/${share.projectId}`);
}

export async function getProjectShares(projectId: string) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  return prisma.projectShare.findMany({
    where: { projectId },
    include: { user: { select: { id: true, name: true, email: true } } },
  });
}
