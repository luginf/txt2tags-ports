use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME             => 'Text::Txt2tags',
    AUTHOR           => 'luginf <verde@aurelio.net>',
    VERSION_FROM     => 'lib/Text/Txt2tags.pm',
    ABSTRACT_FROM    => 'lib/Text/Txt2tags.pm',
    LICENSE          => 'bsd',
    MIN_PERL_VERSION => '5.016',
    PREREQ_PM        => {
        'Carp'         => 0,
        'Scalar::Util' => 0,
        'List::Util'   => 0,
        'POSIX'        => 0,
        'Encode'       => 0,
        'File::Basename' => 0,
        'Getopt::Long' => 0,
    },
    TEST_REQUIRES => {
        'Test::More'      => '0.98',
        'Test::Exception' => 0,
    },
    EXE_FILES => ['bin/txt2tags'],
    META_MERGE => {
        'meta-spec' => { version => 2 },
        resources   => {
            repository => {
                type => 'git',
                url  => 'https://github.com/luginf/txt2tags-ports.git',
                web  => 'https://github.com/luginf/txt2tags-ports',
            },
            bugtracker => {
                web => 'https://github.com/luginf/txt2tags-ports/issues',
            },
        },
    },
);
