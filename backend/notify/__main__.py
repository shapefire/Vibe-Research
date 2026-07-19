"""CLI：cd backend && python -m notify --digest today | --test"""

from __future__ import annotations

import argparse
import sys

from env_loader import load_env_file

load_env_file()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vibe-Research 推送通知")
    parser.add_argument("--digest", choices=["today"], help="推送当日 digest")
    parser.add_argument("--date", help="YYYY-MM-DD（配合 --digest）")
    parser.add_argument("--test", action="store_true", help="发送测试消息")
    parser.add_argument("--provider", choices=["wecom", "feishu"], help="限定渠道")
    args = parser.parse_args(argv)

    if not args.digest and not args.test:
        parser.print_help()
        return 1

    from notify.service import NotifyService
    import digest as digest_mod
    import notes as notes_mod

    svc = NotifyService()

    if args.test:
        results = svc.send_test(args.provider)
        if not results:
            print("notify disabled or no channels", file=sys.stderr)
            return 1
        ok_any = any(r.ok and not r.skipped for r in results) or any(r.ok for r in results)
        for r in results:
            print(f"{r.provider_id}: ok={r.ok} skipped={r.skipped} error={r.error}")
        return 0 if ok_any else 1

    # --digest today
    date = args.date or digest_mod.today_shanghai()
    d = digest_mod.load(date)
    if not d:
        print(f"digest 不存在：{date}，请先运行 jobs/daily_digest.py", file=sys.stderr)
        return 1

    review = notes_mod.get_scheduled_review(date)
    review_content = review.get("content") if review else None
    results = svc.send_digest(d, review_content=review_content)
    if not results:
        print("notify skipped (disabled or no channels)")
        return 0
    for r in results:
        print(f"{r.provider_id}: ok={r.ok} skipped={r.skipped} error={r.error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
