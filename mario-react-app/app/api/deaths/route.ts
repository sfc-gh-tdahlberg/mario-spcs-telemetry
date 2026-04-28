import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const player = searchParams.get("player");
    const playerFilter = player ? `WHERE PLAYER_NAME = '${player.replace(/'/g, "''")}'` : "";

    const rows = await query(`
      SELECT LEVEL, SUM(DEATHS) AS DEATHS
      FROM DIS_MARIO.PUBLIC.DEATHS_BY_LEVEL_LIVE
      ${playerFilter}
      GROUP BY LEVEL
      ORDER BY DEATHS DESC
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Deaths API error:", error);
    return NextResponse.json({ error: "Failed to fetch deaths" }, { status: 500 });
  }
}
