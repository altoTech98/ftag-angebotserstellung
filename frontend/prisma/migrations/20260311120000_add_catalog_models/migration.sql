-- CreateTable
CREATE TABLE "catalog" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "activeVersionId" TEXT,
    "createdBy" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "catalog_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "catalog_version" (
    "id" TEXT NOT NULL,
    "catalogId" TEXT NOT NULL,
    "versionNum" INTEGER NOT NULL,
    "blobUrl" TEXT NOT NULL,
    "fileName" TEXT NOT NULL,
    "fileSize" INTEGER NOT NULL,
    "totalProducts" INTEGER NOT NULL,
    "mainProducts" INTEGER NOT NULL,
    "categories" INTEGER NOT NULL,
    "uploadedBy" TEXT NOT NULL,
    "notes" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT false,
    "validationResult" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "catalog_version_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "product_override" (
    "id" TEXT NOT NULL,
    "catalogId" TEXT NOT NULL,
    "productKey" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "data" JSONB,
    "editedBy" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "product_override_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "product_override_catalogId_productKey_key" ON "product_override"("catalogId", "productKey");

-- AddForeignKey
ALTER TABLE "catalog_version" ADD CONSTRAINT "catalog_version_catalogId_fkey" FOREIGN KEY ("catalogId") REFERENCES "catalog"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "product_override" ADD CONSTRAINT "product_override_catalogId_fkey" FOREIGN KEY ("catalogId") REFERENCES "catalog"("id") ON DELETE CASCADE ON UPDATE CASCADE;
