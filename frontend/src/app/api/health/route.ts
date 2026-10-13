import { NextResponse } from "next/server";

// Lightweight liveness probe for the frontend deployment itself.
// It deliberately reports nothing about the backend or any configuration.
export function GET() {
  return NextResponse.json({ status: "ok" });
}
