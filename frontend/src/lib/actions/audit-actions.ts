'use server';

import prisma from '@/lib/prisma';

export async function logAuditEvent(params: {
  userId: string;
  action: string;
  details: string;
  targetId?: string;
  targetType?: string;
}) {
  return prisma.auditLog.create({
    data: {
      userId: params.userId,
      action: params.action,
      details: params.details,
      targetId: params.targetId,
      targetType: params.targetType,
    },
  });
}

export async function getAuditLog(params: {
  userId?: string;
  action?: string;
  from?: Date;
  to?: Date;
  offset?: number;
  limit?: number;
}) {
  const { userId, action, from, to, offset = 0, limit = 50 } = params;

  const where: Record<string, unknown> = {};
  if (userId) where.userId = userId;
  if (action) where.action = action;
  if (from || to) {
    where.createdAt = {
      ...(from ? { gte: from } : {}),
      ...(to ? { lte: to } : {}),
    };
  }

  const [entries, total] = await Promise.all([
    prisma.auditLog.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      skip: offset,
      take: limit,
      include: {
        user: { select: { name: true, email: true } },
      },
    }),
    prisma.auditLog.count({ where }),
  ]);

  return { entries, total };
}

export async function getActivityFeed(limit = 20) {
  return prisma.auditLog.findMany({
    orderBy: { createdAt: 'desc' },
    take: limit,
    include: {
      user: { select: { name: true, email: true } },
    },
  });
}
