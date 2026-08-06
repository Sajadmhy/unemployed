import type { NextConfig } from "next";
import { fileURLToPath } from "node:url";

const nextConfig: NextConfig = {
  // Pin the workspace root to this app. There are two lockfiles under the
  // project root (this app and web/), and without this Turbopack picks one and
  // resolves everything against the wrong tree.
  turbopack: { root: fileURLToPath(new URL(".", import.meta.url)) },

  // DiceBear is ESM-only and ships its styles as JSON. Leaving both packages
  // external means Next imports them at runtime on the server instead of
  // bundling them, which sidesteps JSON-loader differences between the dev
  // server and the production build. They are only ever imported by route
  // handlers, so nothing here can reach the browser.
  serverExternalPackages: ["@dicebear/core", "@dicebear/styles"],
};

export default nextConfig;
