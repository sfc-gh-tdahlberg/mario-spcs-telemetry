import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const rows = await query(`
      SELECT TO_CHAR(CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', MINUTE::TIMESTAMP_NTZ), 'YYYY-MM-DD"T"HH24:MI:SS') AS MINUTE, EVENT_TYPE, EVENT_COUNT
      FROM DIS_MARIO.PUBLIC.EVENT_TIMELINE_LIVE
      ORDER BY MINUTE DESC
      LIMIT 500
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Timeline API error:", error);
    return NextResponse.json({ error: "Failed to fetch timeline" }, { status: 500 });
  }
}
