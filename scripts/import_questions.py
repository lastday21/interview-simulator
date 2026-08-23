from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_DATA_PATH = Path("data/questions.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or import the interview question catalog."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to the question catalog JSON file.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the catalog without connecting to PostgreSQL.",
    )
    parser.add_argument(
        "--purge-missing",
        action="store_true",
        help=(
            "Permanently delete database questions missing from the catalog. "
            "By default they are only deactivated."
        ),
    )
    return parser.parse_args()


async def main() -> None:
    from app.services import (
        QuestionImportService,
        load_question_rows,
        plan_question_rows,
    )

    args = parse_args()
    rows = load_question_rows(args.path)
    planned_rows, duplicates_skipped = plan_question_rows(rows)

    if args.check:
        topics = {row.topic_title for row in planned_rows}
        subtopics = {(row.topic_title, row.subtopic_title) for row in planned_rows}
        print(
            "Catalog valid: "
            f"questions={len(planned_rows)}, "
            f"topics={len(topics)}, "
            f"subtopics={len(subtopics)}, "
            f"duplicates_skipped={duplicates_skipped}"
        )
        return

    from app.db import get_session_factory

    async with get_session_factory()() as session:
        service = QuestionImportService(session)
        stats = await service.import_rows(
            planned_rows,
            purge_missing=args.purge_missing,
        )
        stats.duplicates_skipped = duplicates_skipped
        await session.commit()

    print(
        "Import completed: "
        f"topics_created={stats.topics_created}, "
        f"topics_deleted={stats.topics_deleted}, "
        f"subtopics_created={stats.subtopics_created}, "
        f"subtopics_deleted={stats.subtopics_deleted}, "
        f"questions_created={stats.questions_created}, "
        f"questions_updated={stats.questions_updated}, "
        f"questions_deactivated={stats.questions_deactivated}, "
        f"questions_deleted={stats.questions_deleted}, "
        f"duplicates_skipped={stats.duplicates_skipped}"
    )


if __name__ == "__main__":
    asyncio.run(main())
