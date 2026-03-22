from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_DATA_PATH = Path("data/all_question_v1.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import normalized interview questions into PostgreSQL."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to normalized questions JSON file.",
    )
    return parser.parse_args()


async def main() -> None:
    from app.db import get_session_factory
    from app.services import (
        QuestionImportService,
        load_question_rows,
        plan_question_rows,
    )

    args = parse_args()
    rows = load_question_rows(args.path)
    planned_rows, duplicates_skipped = plan_question_rows(rows)

    async with get_session_factory()() as session:
        service = QuestionImportService(session)
        stats = await service.import_rows(planned_rows)
        stats.duplicates_skipped = duplicates_skipped
        await session.commit()

    print(
        "Import completed: "
        f"topics_created={stats.topics_created}, "
        f"subtopics_created={stats.subtopics_created}, "
        f"questions_created={stats.questions_created}, "
        f"questions_updated={stats.questions_updated}, "
        f"duplicates_skipped={stats.duplicates_skipped}"
    )


if __name__ == "__main__":
    asyncio.run(main())
