import { auth } from "@/lib/auth";
import prisma from "@/lib/prisma";

export async function seedAdmin() {
  const adminEmail = process.env.DEFAULT_ADMIN_EMAIL;
  const adminPassword = process.env.DEFAULT_ADMIN_PASSWORD;

  if (!adminEmail || !adminPassword) return;

  const existing = await prisma.user.findUnique({
    where: { email: adminEmail },
  });

  if (existing) return;

  // Use Better Auth server API to create user with hashed password
  await auth.api.createUser({
    body: {
      email: adminEmail,
      password: adminPassword,
      name: "Admin",
      role: "admin",
    },
  });

  console.log(`[SEED] Admin user created: ${adminEmail}`);
}
