import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const player = searchParams.get("player");
    const playerFilter = player ? `WHERE PLAYER_NAME = '${player.replace(/'/g, "''")}'` : "";

    const rows = await query(`
      SELECT KEY_NAME, SUM(PRESSES) AS PRESSES
      FROM DIS_MARIO.PUBLIC.KEY_PRESSES_LIVE
      ${playerFilter}
      GROUP BY KEY_NAME
      ORDER BY PRESSES DESC
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Keys API error:", error);
    return NextResponse.json({ error: "Failed to fetch keys" }, { status: 500 });
  }
}
