import csv
import argparse
import json
from itertools import chain


import arrow
import praw
from praw.helpers import flatten_tree


VERSION = '0.0.1'
reddit = praw.Reddit(user_agent='subm/{}'.format(VERSION))


def get_submissions(subreddits, begin, end):
    assert begin < end
    # 期間をしても過不足のある結果が帰ってくるため範囲を大きめに指定する
    a_begin, a_end = begin.replace(days=-1), end.replace(days=+1)
    subrs = '+'.join(subreddits)

    while True:
        query = 'timestamp:{}..{}'.format(a_begin.timestamp, a_end.timestamp)
        subms = reddit.search(
            query, subrs, sort='new', limit=1000, syntax='cloudsearch')

        for s in subms:
            if begin.timestamp <= s.created_utc <= end.timestamp:
                yield s
        else:
            return

        a_end = arrow.get(min(subms, key=lambda s: s.created_utc).created_utc)


def get_comments(subm):
    subm.replace_more_comments(limit=None)
    comms = subm.comments
    flatten_comms = flatten_tree(comms)
    return flatten_comms


def submission_to_dict(subm):
    attrs = [
        'author_flair_css_class',
        'author_flair_text',
        'clicked',
        'created',
        'created_utc',
        'domain',
        'hidden',
        'is_self',
        'likes',
        'link_flair_css_class',
        'link_flair_text',
        'media',
        'media_embed',
        'num_comments',
        'over_18',
        'permalink',
        'saved',
        'score',
        'selftext',
        'selftext_html',
        'thumbnail',
        'title',
        'url',
        'edited',
        'distinguished',
        'stickied',
    ]
    ret = {}
    for a in attrs:
        ret[a] = getattr(subm, a)

    ret['subreddit'] = subm.subreddit.display_name
    ret['subreddit_id'] = subm.subreddit.id
    ret['author'] = subm.author.name

    return ret


def comment_to_dict(comm):
    attrs = [
        'approved_by',
        'author_flair_css_class',
        'author_flair_text',
        'banned_by',
        'body',
        'body_html',
        'created',
        'created_utc',
        'edited',
        'gilded',
        'likes',
        'num_reports',
        'parent_id',
        # 'replies',
        'saved',
        'score',
        'score_hidden',
        'distinguished',
    ]
    ret = {}
    for a in attrs:
        ret[a] = getattr(comm, a)

    subm = comm.submission
    ret['link_author'] = subm.author.name
    ret['link_id'] = subm.id
    ret['link_title'] = subm.title
    ret['link_url'] = subm.url
    ret['subreddit'] = subm.subreddit.display_name
    ret['subreddit_id'] = subm.subreddit.id

    ret['author'] = comm.author.name if comm.author else None

    return ret


def out_submissions(subms, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for subm in subms:
            d = submission_to_dict(subm)
            j = json.dumps(d)
            print(j, file=f)
            yield subm


def out_comments(comms, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for comm in comms:
            d = comment_to_dict(comm)
            j = json.dumps(d)
            print(j, file=f)
            yield comm


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('subreddits', nargs='+')
    p.add_argument('time')
    p.add_argument('-c', '--out-comment', default='comments.jsonl')
    p.add_argument('-s', '--out-submission', default='submissions.jsonl')

    a = p.parse_args()
    return a


def main():
    args = parse_args()

    time = args.time
    if ',' in time:
        times = time.split(',')
        begin = arrow.get(times[0], 'YYYY-MM-DD').floor('day')
        end = arrow.get(times[1], 'YYYY-MM-DD').ceil('day')
    else:
        begin, end = arrow.get(time, 'YYYY-MM-DD').span('day')

    subreddits = args.subreddits
    out_c = args.out_comment
    out_s = args.out_submission

    subms = get_submissions(subreddits, begin, end)
    for c in out_comments(
            chain.from_iterable(get_comments(s) for s in out_submissions(subms, out_s)), out_c):
        pass


if __name__ == '__main__':
    main()
