import { NextResponse } from 'next/server';

// Import state from point route (shared module state)
export async function GET() {
  // Fetch from point endpoint to get current state
  const response = await fetch('http://localhost:3000/api/point', {
    method: 'GET',
    cache: 'no-store',
  });

  const data = await response.json();
  return NextResponse.json(data);
}
