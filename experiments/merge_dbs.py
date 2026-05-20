from mtg_ai.transposition_db import merge_statistics, load_statistics, load_all_results, save_result

def copy_into(src: str, dst: str):
    stats = load_statistics(src)
    results = load_all_results(src, *list(stats.keys()))
    merge_statistics(dst, stats)
    for (game,result) in results.items():
        save_result(dst,game,result)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('dst')
    parser.add_argument('srcs', nargs='*')

    args = parser.parse_args()
    for path in args.srcs:
        print(f'adding {path} to {args.dst}')
        copy_into(path, args.dst)