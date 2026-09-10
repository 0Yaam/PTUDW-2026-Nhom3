import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Small Kitchen | Culinary Blog",
  description: "Find clear recipes and stories from home kitchens.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
