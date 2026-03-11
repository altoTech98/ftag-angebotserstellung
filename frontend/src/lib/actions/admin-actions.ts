'use server';

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';
import { logAuditEvent } from '@/lib/actions/audit-actions';

async function requireAdmin() {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { admin: ['access'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  return session;
}

export async function listUsers(
  search?: string,
  offset?: number,
  limit?: number
) {
  await requireAdmin();
  throw new Error('Nicht implementiert');
}

export async function inviteUser(formData: FormData) {
  await requireAdmin();
  throw new Error('Nicht implementiert');
}

export async function updateUserRole(userId: string, role: string) {
  await requireAdmin();
  throw new Error('Nicht implementiert');
}

export async function toggleUserBan(
  userId: string,
  ban: boolean,
  reason?: string
) {
  await requireAdmin();
  throw new Error('Nicht implementiert');
}

export async function getSystemSettings() {
  await requireAdmin();
  throw new Error('Nicht implementiert');
}

export async function updateAnalyseSettings(formData: FormData) {
  await requireAdmin();
  throw new Error('Nicht implementiert');
}

export async function updateSecuritySettings(formData: FormData) {
  await requireAdmin();
  throw new Error('Nicht implementiert');
}

export async function updateApiKeySettings(formData: FormData) {
  await requireAdmin();
  throw new Error('Nicht implementiert');
}
