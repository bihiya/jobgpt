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
      <body>{children}</body>
    </html>
  );
}
