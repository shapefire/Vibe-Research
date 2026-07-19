"""每日摘要 job —— scheduler 注册 + CLI 入口。"""

from __future__ import annotations

import argparse
import os
import sys

import digest
import notes
import scheduled_review

from scheduler import JobSpec


def run(date: str | None = None) -> digest.DailyDigest:
    d = digest.generate(date)
    digest.save(d)
    notes.create_from_digest(d)
    review_text = scheduled_review.run_for_digest(d)
    try:
        from notify.service import NotifyService

        results = NotifyService().send_digest(d, review_content=review_text)
        for r in results:
            if not r.ok and not r.skipped:
                print(f"[vibe-research] notify {r.provider_id} failed: {r.error}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"[vibe-research] notify skipped: {e}", file=sys.stderr)
    return d


def spec() -> JobSpec:
    cron = os.environ.get("VR_DIGEST_TIME", "18:00").strip()
    return JobSpec(name="daily_digest", cron_time=cron, fn=lambda: run())


def main() -> int:
    parser = argparse.ArgumentParser(description="生成每日数据摘要")
    parser.add_argument("--date", help="YYYY-MM-DD，默认今天（上海时区）")
    args = parser.parse_args()
    if args.date:
        try:
            from datetime import datetime

            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("非法 date 格式，应为 YYYY-MM-DD", file=sys.stderr)
            return 1
    try:
        d = run(args.date)
        print(f"Digest saved: {d.date}")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"Digest failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
