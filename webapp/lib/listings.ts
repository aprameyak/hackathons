import path from 'path';
import fs from 'fs';

export interface Hackathon {
  name: string;
  organizer: string;
  location: string;
  mode: string;
  start_date: string;
  end_date: string;
  open_to: string;
  prize_pool: string;
  url: string;
  date_added: string;
}

export interface ProcessedRow {
  name: string;
  organizer: string;
  location: string;
  mode: string;
  startDate: string;
  endDate: string;
  datesFormatted: string;
  openTo: string;
  prizePool: string;
  url: string;
  dateFormatted: string;
  isUpcoming: boolean;
}

export interface ListingsData {
  listings: ProcessedRow[];
  total: number;
  upcomingCount: number;
}

function getHackathons(): Hackathon[] {
  const filePath = path.resolve(process.cwd(), '..', 'listings.json');
  const raw = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(raw) as Hackathon[];
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function formatDateRange(start: string, end: string): string {
  try {
    const s = new Date(start + 'T00:00:00');
    const e = new Date(end + 'T00:00:00');

    const sMonth = s.toLocaleDateString('en-US', { month: 'short' });
    const eMonth = e.toLocaleDateString('en-US', { month: 'short' });
    const sYear = s.getFullYear();
    const eYear = e.getFullYear();

    if (sYear === eYear && s.getMonth() === e.getMonth()) {
      return `${sMonth} ${s.getDate()}–${e.getDate()}, ${sYear}`;
    } else if (sYear === eYear) {
      return `${sMonth} ${s.getDate()} – ${eMonth} ${e.getDate()}, ${sYear}`;
    } else {
      return `${sMonth} ${s.getDate()}, ${sYear} – ${eMonth} ${e.getDate()}, ${eYear}`;
    }
  } catch {
    return `${start} – ${end}`;
  }
}

function isUpcoming(startDate: string): boolean {
  const today = new Date().toISOString().slice(0, 10);
  return startDate >= today;
}

function processHackathons(hackathons: Hackathon[]): ProcessedRow[] {
  const rows: ProcessedRow[] = hackathons.map((h) => ({
    name: h.name.trim(),
    organizer: h.organizer.trim(),
    location: h.location.trim(),
    mode: h.mode.trim(),
    startDate: h.start_date,
    endDate: h.end_date,
    datesFormatted: formatDateRange(h.start_date, h.end_date),
    openTo: h.open_to.trim(),
    prizePool: h.prize_pool.trim(),
    url: h.url?.trim() ?? '',
    dateFormatted: formatDate(h.date_added),
    isUpcoming: isUpcoming(h.start_date),
  }));

  // Sort: upcoming first by start_date ascending, then past by start_date descending
  const upcoming = rows.filter((r) => r.isUpcoming).sort((a, b) => a.startDate.localeCompare(b.startDate));
  const past = rows.filter((r) => !r.isUpcoming).sort((a, b) => b.startDate.localeCompare(a.startDate));

  return [...upcoming, ...past];
}

export function getAllListingsData(): ListingsData {
  const hackathons = getHackathons();
  const rows = processHackathons(hackathons);
  const upcomingCount = rows.filter((r) => r.isUpcoming).length;
  return {
    listings: rows,
    total: rows.length,
    upcomingCount,
  };
}
