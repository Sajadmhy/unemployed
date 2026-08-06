import { isValidSeed, renderAvatar } from "@/lib/avatar";
import { asGender } from "@/lib/gender-options";

// Reads the query string, so it can never be prerendered.
export const dynamic = "force-dynamic";

/**
 * The only place an avatar is ever drawn.
 *
 * The response is a pure function of the query string, which is what makes the
 * immutable cache header honest: the same seed and gender return byte identical
 * SVG forever. Browsers fetch each avatar once, ever.
 *
 * Open to any origin because the local app renders these too, and because an
 * avatar is not data worth protecting.
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const seed = searchParams.get("seed") ?? "";
  const gender = asGender(searchParams.get("gender"));

  if (!isValidSeed(seed)) {
    return new Response("seed must be 1 to 64 letters, digits or hyphens", {
      status: 400,
    });
  }

  const svg = await renderAvatar(seed, gender);
  return new Response(svg, {
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=31536000, immutable",
      "Access-Control-Allow-Origin": "*",
    },
  });
}
