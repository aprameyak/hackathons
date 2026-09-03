import { getAllListingsData } from '@/lib/listings';
import HackathonsClient from '@/components/HackathonsClient';

export const revalidate = 60;

export default function Home() {
  const data = getAllListingsData();
  return <HackathonsClient data={data} />;
}
