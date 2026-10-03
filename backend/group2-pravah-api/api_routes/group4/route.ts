import { NextResponse } from 'next/server';

const GROUP4_VANA_URL =
  process.env.NEXT_PUBLIC_VANA_GROUP4_URL || 'http://163.128.209.18:8010';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    
    const res = await fetch(`${GROUP4_VANA_URL}/vana/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await res.text();
    
    if (!res.ok) {
      return NextResponse.json(
        { error: `Group 4 API Error: ${data}` },
        { status: res.status }
      );
    }
    
    // Attempt to parse JSON response
    let jsonResp;
    try {
      jsonResp = JSON.parse(data);
    } catch {
      return NextResponse.json({ error: 'Invalid JSON response from Group 4', raw: data }, { status: 500 });
    }

    return NextResponse.json(jsonResp);
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal Server Error while proxying to Group 4', details: String(error) },
      { status: 500 }
    );
  }
}
