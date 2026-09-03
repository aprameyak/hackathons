import type { Metadata } from 'next';
import './globals.css';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://hackathons.vercel.app';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: 'Hackathon Tracker — Upcoming CS Hackathons',
  description:
    'Curated list of upcoming college and high school hackathons. Updated hourly from MLH, Devpost, Devfolio, HackClub, and community sources. Filter by mode (in-person, virtual, hybrid) and eligibility.',
  keywords: [
    'hackathon 2026',
    'hackathon 2027',
    'college hackathon',
    'high school hackathon',
    'MLH hackathon',
    'Devpost hackathon',
    'upcoming hackathons',
    'HackMIT',
    'TreeHacks',
    'HackHarvard',
    'PennApps',
    'MHacks',
    'HackGT',
    'virtual hackathon',
    'in-person hackathon',
    'hackathon tracker',
    'hackathon list',
    'CS hackathon',
  ],
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    title: 'Hackathon Tracker — Upcoming CS Hackathons',
    description:
      'Curated, auto-updated list of upcoming hackathons — in-person, virtual, and hybrid. College and high school. Updated hourly.',
    url: SITE_URL,
    siteName: 'Hackathon Tracker',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary',
    title: 'Hackathon Tracker — Upcoming CS Hackathons',
    description: 'Upcoming hackathons for college and high school students. Updated hourly.',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
