import "./(styles)/globals.css";
import Navigation from './components/Navigation';

export const metadata = {
  title: "recontent",
  description: "AI content for real estate",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans bg-gray-50 min-h-screen">
        <Navigation />
        <main>
          {children}
        </main>
      </body>
    </html>
  );
}
