'use server';

import prisma from '@/lib/prisma';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import { revalidatePath } from 'next/cache';
import { put } from '@vercel/blob';
import { Prisma } from '@/generated/prisma/client';

const PYTHON_BACKEND_URL =
  process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
const PYTHON_SERVICE_KEY = process.env.PYTHON_SERVICE_KEY || '';

// -- Helpers ------------------------------------------------------------------

async function pythonFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${PYTHON_BACKEND_URL}/api${path}`;
  return fetch(url, {
    ...options,
    headers: {
      'X-Service-Key': PYTHON_SERVICE_KEY,
      ...options.headers,
    },
  });
}

// -- Server Actions -----------------------------------------------------------

/**
 * List all catalogs with their active version info.
 */
export async function getCatalogs() {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { catalog: ['read'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  const catalogs = await prisma.catalog.findMany({
    include: {
      versions: {
        where: { isActive: true },
        take: 1,
      },
    },
    orderBy: { updatedAt: 'desc' },
  });

  return catalogs;
}

/**
 * Upload a new catalog file. Validates via Python, creates Prisma records,
 * optionally activates.
 */
export async function uploadCatalog(formData: FormData) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { catalog: ['upload'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  const file = formData.get('file') as File | null;
  if (!file) return { error: 'Keine Datei ausgewaehlt' };

  const catalogName =
    (formData.get('name') as string) || file.name.replace(/\.xlsx$/i, '');
  const notes = (formData.get('notes') as string) || null;
  const autoActivate = formData.get('autoActivate') !== 'false';

  // Upload to Vercel Blob
  const timestamp = Date.now();
  const blob = await put(`catalogs/${timestamp}_${file.name}`, file, {
    access: 'public',
  });

  // Validate via Python
  const validateResp = await pythonFetch('/catalog/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ blob_url: blob.url }),
  });

  if (!validateResp.ok) {
    return {
      error: 'Validierung fehlgeschlagen',
      validation: null,
    };
  }

  const validation = (await validateResp.json()) as {
    valid: boolean;
    total_rows: number;
    main_products: number;
    categories: number;
    errors: string[];
    warnings: string[];
  };

  if (!validation.valid) {
    return {
      error: 'Katalog-Validierung fehlgeschlagen',
      validation,
    };
  }

  // Find or create Catalog record
  let catalog = await prisma.catalog.findFirst({
    where: { name: catalogName },
  });

  if (!catalog) {
    catalog = await prisma.catalog.create({
      data: {
        name: catalogName,
        createdBy: session.user.id,
      },
    });
  }

  // Determine next version number
  const lastVersion = await prisma.catalogVersion.findFirst({
    where: { catalogId: catalog.id },
    orderBy: { versionNum: 'desc' },
  });
  const nextVersionNum = (lastVersion?.versionNum ?? 0) + 1;

  // Create CatalogVersion
  const version = await prisma.catalogVersion.create({
    data: {
      catalogId: catalog.id,
      versionNum: nextVersionNum,
      blobUrl: blob.url,
      fileName: file.name,
      fileSize: file.size,
      totalProducts: validation.total_rows,
      mainProducts: validation.main_products,
      categories: validation.categories,
      uploadedBy: session.user.id,
      notes,
      isActive: false,
      validationResult: validation as unknown as Prisma.InputJsonValue,
    },
  });

  // Auto-activate if first version or explicitly requested
  if (autoActivate || nextVersionNum === 1) {
    // Deactivate current active version
    if (lastVersion?.isActive) {
      await prisma.catalogVersion.update({
        where: { id: lastVersion.id },
        data: { isActive: false },
      });
    }

    // Activate new version
    await prisma.catalogVersion.update({
      where: { id: version.id },
      data: { isActive: true },
    });

    await prisma.catalog.update({
      where: { id: catalog.id },
      data: { activeVersionId: version.id },
    });

    // Tell Python to activate
    await pythonFetch('/catalog/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blob_url: blob.url }),
    });
  }

  revalidatePath('/katalog');
  return {
    success: true,
    validation,
    catalogId: catalog.id,
    versionId: version.id,
  };
}

/**
 * Browse products from the active catalog with search/filter/pagination.
 * Merges ProductOverride records from Prisma.
 */
export async function getCatalogProducts(
  catalogId: string,
  search?: string,
  category?: string,
  page?: number
) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { catalog: ['read'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  // Fetch from Python
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (category) params.set('category', category);
  if (page) params.set('page', String(page));
  params.set('limit', '50');

  const resp = await pythonFetch(`/catalog/products?${params.toString()}`);
  if (!resp.ok) {
    return { error: 'Produkte konnten nicht geladen werden' };
  }

  const data = (await resp.json()) as {
    products: Array<{
      row_index: number;
      category: string;
      summary: string;
      fields: Record<string, unknown>;
      kostentraeger: string;
    }>;
    total: number;
    page: number;
    limit: number;
    pages: number;
  };

  // Load overrides for this catalog
  const overrides = await prisma.productOverride.findMany({
    where: { catalogId },
  });

  const overrideMap = new Map(
    overrides.map((o) => [o.productKey, o])
  );

  // Merge override status into products
  const products = data.products.map((p) => {
    const override = overrideMap.get(p.kostentraeger || String(p.row_index));
    return {
      ...p,
      hasOverride: !!override,
      overrideAction: override?.action ?? null,
      overrideId: override?.id ?? null,
    };
  });

  return {
    products,
    total: data.total,
    page: data.page,
    limit: data.limit,
    pages: data.pages,
  };
}

/**
 * Get version history for a catalog.
 */
export async function getCatalogVersions(catalogId: string) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { catalog: ['read'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  return prisma.catalogVersion.findMany({
    where: { catalogId },
    orderBy: { versionNum: 'desc' },
  });
}

/**
 * Rollback to a previous catalog version.
 */
export async function rollbackVersion(
  catalogId: string,
  versionId: string
) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { catalog: ['update'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  const targetVersion = await prisma.catalogVersion.findUnique({
    where: { id: versionId },
  });
  if (!targetVersion || targetVersion.catalogId !== catalogId) {
    return { error: 'Version nicht gefunden' };
  }

  // Deactivate current active version
  await prisma.catalogVersion.updateMany({
    where: { catalogId, isActive: true },
    data: { isActive: false },
  });

  // Activate target version
  await prisma.catalogVersion.update({
    where: { id: versionId },
    data: { isActive: true },
  });

  await prisma.catalog.update({
    where: { id: catalogId },
    data: { activeVersionId: versionId },
  });

  // Tell Python to activate this version's blob
  await pythonFetch('/catalog/activate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ blob_url: targetVersion.blobUrl }),
  });

  revalidatePath('/katalog');
  return { success: true };
}

/**
 * Get diff between two catalog versions.
 */
export async function compareVersions(
  oldVersionId: string,
  newVersionId: string
) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { catalog: ['read'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  const [oldVersion, newVersion] = await Promise.all([
    prisma.catalogVersion.findUnique({ where: { id: oldVersionId } }),
    prisma.catalogVersion.findUnique({ where: { id: newVersionId } }),
  ]);

  if (!oldVersion || !newVersion) {
    return { error: 'Version nicht gefunden' };
  }

  const resp = await pythonFetch('/catalog/diff', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      old_blob_url: oldVersion.blobUrl,
      new_blob_url: newVersion.blobUrl,
    }),
  });

  if (!resp.ok) {
    return { error: 'Vergleich fehlgeschlagen' };
  }

  return resp.json();
}

/**
 * Save a product override (edit, add, or delete).
 */
export async function saveProductOverride(
  catalogId: string,
  productKey: string,
  action: string,
  data?: Record<string, unknown>
) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { catalog: ['update'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  const override = await prisma.productOverride.upsert({
    where: {
      catalogId_productKey: { catalogId, productKey },
    },
    create: {
      catalogId,
      productKey,
      action,
      data: (data ?? Prisma.JsonNull) as Prisma.InputJsonValue,
      editedBy: session.user.id,
    },
    update: {
      action,
      data: (data ?? Prisma.JsonNull) as Prisma.InputJsonValue,
      editedBy: session.user.id,
    },
  });

  revalidatePath('/katalog');
  return override;
}

/**
 * Delete a product override (revert to original catalog data).
 */
export async function deleteProductOverride(overrideId: string) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) throw new Error('Nicht authentifiziert');

  const hasPermission = await auth.api.userHasPermission({
    body: { userId: session.user.id, permissions: { catalog: ['update'] } },
  });
  if (!hasPermission.success) throw new Error('Keine Berechtigung');

  await prisma.productOverride.delete({
    where: { id: overrideId },
  });

  revalidatePath('/katalog');
}
