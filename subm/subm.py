import csv
import argparse
import sys

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

    created_set = set()
    while True:
        query = 'timestamp:{}..{}'.format(a_begin.timestamp, a_end.timestamp)
        subms = reddit.search(
            query, subrs, sort='new', limit=1000, syntax='cloudsearch')

        subms = list(subms)
        no_content = True
        for s in subms:
            if begin.timestamp <= s.created_utc <= end.timestamp:
                no_content = False
                created_set.add(s.created_utc)
                yield s

        if no_content:
            return

        a_end = arrow.get(min(created_set))


def get_comments(subm):
    subm.replace_more_comments(limit=None)
    comms = subm.comments
    flatten_comms = flatten_tree(comms)
    return flatten_comms


def submission_to_dict(subm):
    attrs = [
        'author_flair_text',
        'created',
        'created_utc',
        'domain',
        'id',
        'is_self',
        'link_flair_text',
        'name',
        'num_comments',
        'over_18',
        'permalink',
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
    ret['author'] = subm.author.name

    return ret

submission_keys = sorted([
    'author',
    'author_flair_text',
    'created',
    'created_utc',
    'domain',
    'distinguished',
    'edited',
    'id',
    'is_self',
    'link_flair_text',
    'name',
    'num_comments',
    'over_18',
    'permalink',
    'score',
    'selftext',
    'selftext_html',
    'stickied',
    'subreddit',
    'thumbnail',
    'title',
    'url',
])


def comment_to_dict(comm):
    attrs = [
        'author_flair_text',
        'body',
        'body_html',
        'created',
        'created_utc',
        'edited',
        'gilded',
        'id',
        'name',
        'num_reports',
        'parent_id',
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

    ret['author'] = comm.author.name if comm.author else None
    return ret

comment_keys = sorted([
    'author',
    'author_flair_text',
    'body',
    'body_html',
    'created',
    'created_utc',
    'distinguished',
    'edited',
    'gilded',
    'id',
    'name',
    'link_author',
    'link_id',
    'link_title',
    'link_url',
    'num_reports',
    'parent_id',
    'score',
    'score_hidden',
    'subreddit',
])


def out_submissions(subms, writer):
    for subm in subms:
        d = submission_to_dict(subm)
        writer.write(d)
        yield subm


def out_comments(comms, writer):
    for comm in comms:
        d = comment_to_dict(comm)
        writer.write(d)
        yield comm


class Writer:

    def __init__(self, file):
        self.file = file

    def write(self, d):
        raise NotImplemented

    def __enter__(self):
        pass

    def __exit__(self, *args):
        self.file.close()


class NullWriter(Writer):

    def __init__(self):
        pass

    def write(self, d):
        pass

    def __exit__(self, *args):
        pass


class CSVWriter(Writer):

    def __init__(self, fields, file):
        self.writer = csv.DictWriter(file, fields)
        self.writer.writeheader()
        super().__init__(file)

    def write(self, d):
        self.writer.writerow(d)


class Progress:

    def __init__(self, begin, end):
        self.begin = begin
        self.end = end
        self.num = 0

    def update(self, at):
        self.num += 1
        all_width = self.end - self.begin

        estimate = (all_width / (self.end - at)) * self.num

        sys.stderr.write(
            '\rrest {:^10d}/{:^10d}'.format(self.num, int(estimate)))
        sys.stderr.flush()


def download(subreddits, begin, end, s_out, c_out, progress, is_comment):
    subms = get_submissions(subreddits, begin, end)
    for subm in out_submissions(subms, s_out):
        if is_comment:
            for c in out_comments(get_comments(subm), c_out):
                pass
        progress.update(arrow.get(subm.created_utc))


def parse_args():
    p = argparse.ArgumentParser(
        description='A tool downloads reddit\'s submissions and comments')
    p.add_argument('subreddit', nargs='+', help='target subreddits')
    p.add_argument('time',
                   help='submission period (example: "2015-09-08", "2015-09-02,2015-09-12")')
    p.add_argument('-c', '--comment', nargs='?', const='comments.csv', default='', metavar='FILE',
                   help='file stores comments data. If not provided, it is not requested. If FILE not provided, default file is "%(const)s".')
    p.add_argument('-s', '--submission', default='submissions.csv', metavar='FILE',
                   help='file stores submissions data. (default: "%(default)s").')

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

    subreddits = args.subreddit
    c_out_file = args.comment
    s_out_file = args.submission
    is_comment = bool(c_out_file)

    s_file = open(s_out_file, 'w', encoding='utf-8', newline='')
    s_out = CSVWriter(submission_keys, s_file)
    if c_out_file:
        c_file = open(c_out_file, 'w', encoding='utf-8', newline='')
        c_out = CSVWriter(comment_keys, c_file)
    else:
        c_out = NullWriter()

    prog = Progress(begin, end)
    with s_out, c_out:
        download(subreddits, begin, end, s_out, c_out, prog, is_comment)

if __name__ == '__main__':
    main()
