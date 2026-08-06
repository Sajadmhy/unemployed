import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

/**
 * The wordmark reduced to what survives at 32 pixels: a struck-through "u".
 * Drawn rather than shipped as a file so it stays in step with the mark itself.
 */
export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#000",
          color: "#fff",
          fontSize: 24,
          fontWeight: 700,
          fontFamily: "monospace",
          position: "relative",
        }}
      >
        u
        <div
          style={{
            position: "absolute",
            left: 5,
            right: 5,
            top: 16,
            height: 3,
            background: "#fff",
          }}
        />
      </div>
    ),
    size,
  );
}
