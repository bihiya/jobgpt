import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'JobPilot AI — Automate your job search',
  description:
    'Configure once. JobPilot scans portals, ranks matches with AI, and applies with human-in-the-loop control.',
  openGraph: {
    title: 'JobPilot AI',
    description: 'AI-powered job automation with approval workflows.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Sofia+Sans:wght@400;600;700;800&family=Sora:wght@600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
