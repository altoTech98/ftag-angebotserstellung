import { createAccessControl } from "better-auth/plugins/access";

// Define resources and their available actions
const statement = {
  analysis: ["create", "read"],
  project: ["create", "read", "update", "delete", "share"],
  catalog: ["read", "update", "upload"],
  admin: ["access", "manage-users", "manage-settings"],
} as const;

export const ac = createAccessControl(statement);

// Tiered roles -- each role level includes the permissions of the level below
export const viewerRole = ac.newRole({
  analysis: ["read"],
  project: ["read"],
  catalog: ["read"],
});

export const analystRole = ac.newRole({
  analysis: ["create", "read"],
  project: ["read"],
  catalog: ["read"],
});

export const managerRole = ac.newRole({
  analysis: ["create", "read"],
  project: ["create", "read", "update", "delete", "share"],
  catalog: ["read", "update", "upload"],
});

export const adminRole = ac.newRole({
  analysis: ["create", "read"],
  project: ["create", "read", "update", "delete", "share"],
  catalog: ["read", "update", "upload"],
  admin: ["access", "manage-users", "manage-settings"],
});
