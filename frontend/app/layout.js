export const metadata = {
  title: "Melooha: Show Your Work",
  description: "See the birth chart behind every answer.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body
        style={{
          margin: 0,
          fontFamily: "system-ui, sans-serif",
          background: "#14091a",
          color: "#f4eaf7",
        }}
      >
        {children}
      </body>
    </html>
  );
}
