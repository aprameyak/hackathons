'use client';

import { useState, useMemo } from 'react';
import type { ListingsData, ProcessedRow } from '@/lib/listings';

function ApplyButton({ url }: { url: string }) {
  if (!url) {
    return <span title="Registration closed">🔒</span>;
  }
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 transition-colors whitespace-nowrap"
    >
      Apply
    </a>
  );
}

function ModeBadge({ mode }: { mode: string }) {
  const colors: Record<string, string> = {
    'In-Person': 'bg-green-100 text-green-700',
    'Virtual': 'bg-purple-100 text-purple-700',
    'Hybrid': 'bg-yellow-100 text-yellow-700',
  };
  const cls = colors[mode] ?? 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${cls}`}>
      {mode}
    </span>
  );
}

function HackathonTable({
  rows,
  search,
  modeFilter,
  openToFilter,
  showUpcomingOnly,
}: {
  rows: ProcessedRow[];
  search: string;
  modeFilter: string;
  openToFilter: string;
  showUpcomingOnly: boolean;
}) {
  const displayRows = useMemo(() => {
    return rows.filter((row) => {
      if (showUpcomingOnly && !row.isUpcoming) return false;
      if (modeFilter && row.mode !== modeFilter) return false;
      if (openToFilter && row.openTo !== openToFilter) return false;
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        row.name.toLowerCase().includes(q) ||
        row.organizer.toLowerCase().includes(q) ||
        row.location.toLowerCase().includes(q) ||
        row.datesFormatted.toLowerCase().includes(q)
      );
    });
  }, [rows, search, modeFilter, openToFilter, showUpcomingOnly]);

  if (displayRows.length === 0) {
    return (
      <div className="py-12 text-center text-gray-500">
        No hackathons match your filters.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
            <th className="px-4 py-3 w-44">Hackathon</th>
            <th className="px-4 py-3 w-36">Organizer</th>
            <th className="px-4 py-3 w-36">Location</th>
            <th className="px-4 py-3 w-24">Mode</th>
            <th className="px-4 py-3 w-40">Dates</th>
            <th className="px-4 py-3 w-28">Open To</th>
            <th className="px-4 py-3 w-24">Prize</th>
            <th className="px-4 py-3 w-20">Apply</th>
            <th className="px-4 py-3 w-20">Added</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {displayRows.map((row, i) => (
            <tr
              key={i}
              className={`hover:bg-blue-50 transition-colors ${!row.isUpcoming ? 'opacity-60' : ''}`}
            >
              <td className="px-4 py-2.5 align-top font-medium text-gray-900">
                {row.name}
              </td>
              <td className="px-4 py-2.5 align-top text-gray-600">{row.organizer}</td>
              <td className="px-4 py-2.5 align-top text-gray-600">{row.location}</td>
              <td className="px-4 py-2.5 align-top">
                <ModeBadge mode={row.mode} />
              </td>
              <td className="px-4 py-2.5 align-top text-gray-600 whitespace-nowrap">
                {row.datesFormatted}
              </td>
              <td className="px-4 py-2.5 align-top text-gray-600">{row.openTo}</td>
              <td className="px-4 py-2.5 align-top text-gray-600 whitespace-nowrap">
                {row.prizePool}
              </td>
              <td className="px-4 py-2.5 align-top">
                <ApplyButton url={row.url} />
              </td>
              <td className="px-4 py-2.5 align-top text-gray-500 whitespace-nowrap">
                {row.dateFormatted}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const MODES = ['In-Person', 'Virtual', 'Hybrid'];
const OPEN_TO_OPTIONS = ['College', 'High School', 'Grad', 'All'];

export default function HackathonsClient({ data }: { data: ListingsData }) {
  const [search, setSearch] = useState('');
  const [modeFilter, setModeFilter] = useState('');
  const [openToFilter, setOpenToFilter] = useState('');
  const [showUpcomingOnly, setShowUpcomingOnly] = useState(true);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">
              Hackathon Tracker
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              {data.upcomingCount} upcoming &middot; {data.total} total &middot; updated hourly
            </p>
          </div>
          <a
            href="https://github.com/aprameyak/hackathons"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View on GitHub"
            className="text-gray-400 hover:text-gray-700 transition-colors mt-1"
          >
            <svg height="20" width="20" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <input
            type="search"
            placeholder="Search by name, organizer, or location..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-md rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm shadow-sm placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />

          <select
            value={modeFilter}
            onChange={(e) => setModeFilter(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All modes</option>
            {MODES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>

          <select
            value={openToFilter}
            onChange={(e) => setOpenToFilter(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All participants</option>
            {OPEN_TO_OPTIONS.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>

          <label className="flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showUpcomingOnly}
              onChange={(e) => setShowUpcomingOnly(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Upcoming only
          </label>

          <div className="relative group">
            <button
              className="flex h-8 w-8 items-center justify-center rounded-full border border-gray-300 text-xs text-gray-400 hover:border-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Legend"
            >
              ?
            </button>
            <div className="pointer-events-none absolute left-0 top-10 z-20 w-60 rounded-lg border border-gray-200 bg-white p-3 shadow-lg opacity-0 group-hover:opacity-100 transition-opacity text-xs text-gray-600">
              <p className="mb-2 font-semibold text-gray-800">Legend</p>
              <ul className="space-y-1.5">
                <li><span className="font-medium">🔒</span> — registration closed</li>
                <li><span className="inline-block rounded px-1 bg-green-100 text-green-700 font-medium">In-Person</span> — attend on-site</li>
                <li><span className="inline-block rounded px-1 bg-purple-100 text-purple-700 font-medium">Virtual</span> — participate online</li>
                <li><span className="inline-block rounded px-1 bg-yellow-100 text-yellow-700 font-medium">Hybrid</span> — in-person or online</li>
                <li><span className="text-gray-400">Dimmed rows</span> — past events</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
          <HackathonTable
            rows={data.listings}
            search={search}
            modeFilter={modeFilter}
            openToFilter={openToFilter}
            showUpcomingOnly={showUpcomingOnly}
          />
        </div>

        <p className="mt-4 text-center text-xs text-gray-400">
          If this helped you,{' '}
          <a
            href="https://github.com/aprameyak/hackathons"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-gray-600"
          >
            star the repo
          </a>
          {' '}— it helps others find it &middot; 🔒 = registration closed
        </p>
      </main>
    </div>
  );
}
