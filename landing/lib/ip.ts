import { createHash } from "node:crypto";

/** Hashed, never stored raw. On Vercel the client is the first entry. */
export function ipHash(request: Request): string {
  const forwarded = request.headers.get("x-forwarded-for");
  const ip = forwarded?.split(",")[0]?.trim() || "local";
  return createHash("sha256")
    .update(ip + (process.env.SIGNUP_IP_SALT ?? "unsalted-dev"))
    .digest("hex");
}

export function isUniqueViolation(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && error.code === "23505";
}
