path = "d:/ai-platform-project/ai-research-platform-fe/src/server/auth.ts"
code = """import { cache } from "react";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getServerApiBaseUrl } from "@/lib/api/config";
import {
  AUTH_COOKIE_NAME,
  type AuthUser,
  CHANGE_PASSWORD_PATH,
  SESSION_INVALID_CODES,
  toAuthUser,
} from "@/lib/auth/auth-config";
import type { CurrentUser } from "@/lib/auth/types";
import { ApiError, type ApiResponse } from "@/types/api";

export const getCurrentSession = cache(async (): Promise<CurrentUser | null> => {
  const session = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!session) return null;

  try {
    const response = await fetch(`${getServerApiBaseUrl()}/auth/me`, {
      headers: { Cookie: `${AUTH_COOKIE_NAME}=${session}` },
      credentials: "include",
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    const body: ApiResponse<CurrentUser> = await response.json();
    if (!body.success) {
      if (SESSION_INVALID_CODES.includes(body.error.code)) return null;
      throw new ApiError(response.status, body.error.code, body.message, body.error.details, body.meta.request_id);
    }
    if (!response.ok) throw new Error("Unable to validate session");
    return body.data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    console.warn("Unable to reach auth service or validate session:", error);
    return null;
  }
});

export async function getAuthenticatedUser(projectId?: string): Promise<AuthUser | null> {
  const current = await getCurrentSession();
  if (current?.user.must_change_password) redirect(CHANGE_PASSWORD_PATH);
  return current ? toAuthUser(current, projectId) : null;
}
"""

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("Updated auth.ts successfully!")
