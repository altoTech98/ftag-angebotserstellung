import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { admin } from "better-auth/plugins";
import { emailOTP } from "better-auth/plugins";
import { nextCookies } from "better-auth/next-js";
import prisma from "@/lib/prisma";
import {
  ac,
  viewerRole,
  analystRole,
  managerRole,
  adminRole,
} from "@/lib/permissions";

export const auth = betterAuth({
  database: prismaAdapter(prisma, { provider: "postgresql" }),
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    maxPasswordLength: 128,
    requireEmailVerification: false, // invite-only, admin creates users
    disableSignUp: true,
  },
  session: {
    expiresIn: 60 * 60 * 8, // 8 hours (28800 seconds)
    updateAge: 60 * 15, // refresh every 15 minutes (900 seconds)
  },
  plugins: [
    admin({
      ac,
      roles: {
        viewer: viewerRole,
        analyst: analystRole,
        manager: managerRole,
        admin: adminRole,
      },
      defaultRole: "viewer",
      adminRoles: ["admin"],
    }),
    emailOTP({
      otpLength: 6,
      expiresIn: 600, // 10 minutes
      async sendVerificationOTP({ email, otp, type }) {
        // Email sending -- placeholder until INFRA-05 (Phase 15)
        console.log(`[DEV] OTP for ${email}: ${otp} (type: ${type})`);
      },
    }),
    nextCookies(), // Must be last plugin
  ],
  trustedOrigins: [process.env.BETTER_AUTH_URL!],
});
