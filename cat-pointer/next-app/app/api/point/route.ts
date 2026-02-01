import { NextRequest, NextResponse } from 'next/server';

// Global state (in production, use Redis or similar)
let currentTarget: string | null = null;
let lastUpdated: number = Date.now();

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { target } = body;

    if (!target || !['萝卜', '纸巾', '米奇'].includes(target)) {
      return NextResponse.json(
        { error: 'Invalid target. Must be one of: 萝卜, 纸巾, 米奇' },
        { status: 400 }
      );
    }

    currentTarget = target;
    lastUpdated = Date.now();

    return NextResponse.json({
      success: true,
      target: currentTarget,
      timestamp: lastUpdated,
    });
  } catch {
    return NextResponse.json(
      { error: 'Invalid request body' },
      { status: 400 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    target: currentTarget,
    timestamp: lastUpdated,
  });
}
