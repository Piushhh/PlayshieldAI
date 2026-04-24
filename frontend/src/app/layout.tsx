import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IP Guardian — Content Protection Platform",
  description:
    "Detect unauthorized reuse of protected image and video assets with AI-powered matching.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
