import "./(styles)/globals.css";

export const metadata = {
  title: "recontent",
  description: "AI content for real estate",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans">
        <main className="container py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
