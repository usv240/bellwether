import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  fallback: ["system-ui", "Segoe UI", "Arial", "sans-serif"],
});

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  fallback: ["Consolas", "Menlo", "monospace"],
});

export const metadata: Metadata = {
  title: "Bellwether",
  description:
    "Speech is a vital sign. Bellwether uses the Bee wristband you already wear to learn how you normally speak, and shows you, in numbers you own, when that changes. Not a diagnosis. Evidence for a better conversation with your doctor.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

/*
  Theme is applied before first paint. Light is the default on every page,
  whatever the system preference: data-theme is always stamped, "dark" only
  when the visitor chose it with the toggle, so the prefers-color-scheme
  rule (guarded by :not([data-theme="light"])) never matches by default.
  Stored choice read inside try/catch: storage can be unavailable.
*/
const themeScript = `(function(){var t="light";try{if(localStorage.getItem("bw-theme")==="dark"){t="dark";}}catch(e){}document.documentElement.setAttribute("data-theme",t);})();`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${inter.variable} ${mono.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
