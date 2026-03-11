import { createAuthClient } from "better-auth/react";
import { adminClient } from "better-auth/client/plugins";
import { emailOTPClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  plugins: [adminClient(), emailOTPClient()],
});

export const { signIn, signUp, signOut, useSession } = authClient;
