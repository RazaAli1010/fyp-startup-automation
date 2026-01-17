import "./globals.css";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

export const metadata = {
  title: "Startup Automation Agent",
  description: "Validate your startup idea using AI",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <main className="min-h-screen px-6 py-10">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
