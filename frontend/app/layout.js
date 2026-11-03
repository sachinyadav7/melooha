import "./globals.css";

export const metadata = {
  title: "Melooha: Show Your Work",
  description: "See the birth chart behind every answer.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0b0713",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
