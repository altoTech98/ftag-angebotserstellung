'use server';

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';
import { logAuditEvent } from '@/lib/actions/audit-actions';
import { randomUUID } from 'crypto';
import { resend, EMAIL_FROM } from '@/lib/email';
import { UserInvitationEmail } from '@/emails/user-invitation';

async function requireAdminPermission(permission: 'manage-users' | 'manage-settings') {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { admin: [permission] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  return session;
}

export async function listUsers(
  search?: string,
  offset: number = 0,
  limit: number = 50
) {
  await requireAdminPermission('manage-users');

  const result = await auth.api.listUsers({
    query: {
      searchValue: search || '',
      searchField: 'name',
      limit,
      offset,
    },
  });

  return { users: result.users, total: result.total };
}

export async function inviteUser(formData: FormData) {
  const session = await requireAdminPermission('manage-users');

  const name = formData.get('name') as string;
  const email = formData.get('email') as string;
  const role = formData.get('role') as string;

  if (!name || !email || !role) {
    throw new Error('Name, E-Mail und Rolle sind erforderlich');
  }

  const user = await auth.api.createUser({
    body: {
      email,
      password: randomUUID(),
      name,
      role,
    },
  });

  // Send invitation email (fire-and-forget)
  try {
    await resend.emails.send({
      from: EMAIL_FROM,
      to: [email],
      subject: 'Einladung zur FTAG Angebotserstellung',
      react: UserInvitationEmail({
        name,
        invitedBy: session.user.name || 'Admin',
        loginUrl: `${process.env.BETTER_AUTH_URL}/login`,
      }),
    });
  } catch (error) {
    console.error(`Failed to send invitation email to ${email}:`, error);
  }

  // Fire-and-forget audit log
  logAuditEvent({
    userId: session.user.id,
    action: 'user_invited',
    details: `${name} (${email}) als ${role} eingeladen`,
    targetId: user.id,
    targetType: 'user',
  });

  revalidatePath('/admin');
  return user;
}

export async function updateUserRole(userId: string, role: string) {
  const session = await requireAdminPermission('manage-users');

  await auth.api.setRole({
    body: { userId, role },
  });

  // Fire-and-forget audit log
  logAuditEvent({
    userId: session.user.id,
    action: 'role_changed',
    details: `Rolle geaendert zu ${role}`,
    targetId: userId,
    targetType: 'user',
  });

  revalidatePath('/admin');
}

export async function toggleUserBan(
  userId: string,
  ban: boolean,
  reason?: string
) {
  const session = await requireAdminPermission('manage-users');

  if (ban) {
    await auth.api.banUser({
      body: { userId, banReason: reason },
    });
  } else {
    await auth.api.unbanUser({
      body: { userId },
    });
  }

  // Fire-and-forget audit log
  logAuditEvent({
    userId: session.user.id,
    action: ban ? 'user_deactivated' : 'user_activated',
    details: ban
      ? `Benutzer deaktiviert${reason ? `: ${reason}` : ''}`
      : 'Benutzer aktiviert',
    targetId: userId,
    targetType: 'user',
  });

  revalidatePath('/admin');
}

export async function getSystemSettings() {
  await requireAdminPermission('manage-settings');

  const settings = await prisma.systemSettings.findUnique({
    where: { id: 'default' },
  });

  if (!settings) {
    return {
      id: 'default',
      defaultConfidence: 0.7,
      maxUploadSizeMB: 50,
      sessionTimeoutMin: 480,
      validationPasses: 1,
      claudeApiKey: null as string | null,
      updatedAt: new Date(),
      updatedBy: null as string | null,
    };
  }

  // Mask API key: show only last 4 chars
  const maskedKey = settings.claudeApiKey
    ? `****${settings.claudeApiKey.slice(-4)}`
    : null;

  return {
    ...settings,
    claudeApiKey: maskedKey,
  };
}

export async function updateAnalyseSettings(formData: FormData) {
  const session = await requireAdminPermission('manage-settings');

  const defaultConfidence = parseFloat(formData.get('defaultConfidence') as string);
  const maxUploadSizeMB = parseInt(formData.get('maxUploadSizeMB') as string, 10);
  const validationPasses = parseInt(formData.get('validationPasses') as string, 10);

  if (isNaN(defaultConfidence) || isNaN(maxUploadSizeMB) || isNaN(validationPasses)) {
    throw new Error('Ungueltige Eingabewerte');
  }

  await prisma.systemSettings.upsert({
    where: { id: 'default' },
    update: {
      defaultConfidence,
      maxUploadSizeMB,
      validationPasses,
      updatedBy: session.user.id,
    },
    create: {
      id: 'default',
      defaultConfidence,
      maxUploadSizeMB,
      validationPasses,
      updatedBy: session.user.id,
    },
  });

  // Fire-and-forget audit log
  logAuditEvent({
    userId: session.user.id,
    action: 'settings_changed',
    details: 'Analyse-Einstellungen aktualisiert',
  });

  revalidatePath('/admin');
}

export async function updateSecuritySettings(formData: FormData) {
  const session = await requireAdminPermission('manage-settings');

  const sessionTimeoutMin = parseInt(formData.get('sessionTimeoutMin') as string, 10);

  if (isNaN(sessionTimeoutMin)) {
    throw new Error('Ungueltige Eingabewerte');
  }

  await prisma.systemSettings.upsert({
    where: { id: 'default' },
    update: {
      sessionTimeoutMin,
      updatedBy: session.user.id,
    },
    create: {
      id: 'default',
      sessionTimeoutMin,
      updatedBy: session.user.id,
    },
  });

  // Fire-and-forget audit log
  logAuditEvent({
    userId: session.user.id,
    action: 'settings_changed',
    details: 'Sicherheits-Einstellungen aktualisiert',
  });

  revalidatePath('/admin');
}

export async function updateApiKeySettings(formData: FormData) {
  const session = await requireAdminPermission('manage-settings');

  const claudeApiKey = formData.get('claudeApiKey') as string;

  if (!claudeApiKey) {
    throw new Error('API-Schluessel ist erforderlich');
  }

  await prisma.systemSettings.upsert({
    where: { id: 'default' },
    update: {
      claudeApiKey,
      updatedBy: session.user.id,
    },
    create: {
      id: 'default',
      claudeApiKey,
      updatedBy: session.user.id,
    },
  });

  // Fire-and-forget audit log
  logAuditEvent({
    userId: session.user.id,
    action: 'api_key_changed',
    details: 'API-Schluessel aktualisiert',
  });

  revalidatePath('/admin');
}
