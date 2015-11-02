# subm

This is a tool that downloads Reddit's submissions or comments.
You can get the data for the specified period without number restrictions.

## Installation

This project supports Python 3.

```sh
$ git clone https://github.com/demmc/subm
$ cd subm
$ python setup.py install
```

## Usage

This downloads submissions of r/news of April 1.

```sh
$ subm news 2015-04-01
[===============================================] 140
$ ls
submissions.csv
```

This downloads submissions and comments of r/news from April 1 to April 2.
This is slow.

```sh
$ subm news 2015-04-01,2015-04-02 --comment
[===============================================] 281
$ ls
submissions.csv comments.csv
```

## Licence

GPL
