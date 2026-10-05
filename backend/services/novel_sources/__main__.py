import argparse
import asyncio
import json

from . import search_novel, build_ai_payload, InsufficientNovelDataError


def main():
    parser = argparse.ArgumentParser(description='Search real providers; never substitute mock data.')
    parser.add_argument('title')
    parser.add_argument('author')
    parser.add_argument('--limit', type=int, default=3)
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--description')
    parser.add_argument('--source-url')
    parser.add_argument('--ai-payload', action='store_true', help='Show Person 4 input shape with empty preferences; no Gemini call.')
    args = parser.parse_args()
    try:
        result = asyncio.run(search_novel(args.title, args.author, limit=args.limit, page=args.page,
            user_provided_description=args.description, user_provided_source_url=args.source_url))
        if args.ai_payload:
            result = build_ai_payload(result, {})
    except (ValueError, InsufficientNovelDataError) as exc:
        parser.exit(2, str(exc) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
