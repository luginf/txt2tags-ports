#!/usr/bin/perl
use strict;
use warnings;
use Test::More;
use File::Basename qw(basename dirname);
use File::Spec;
use IPC::Open3;
use Symbol qw(gensym);

# Run txt2tags on each .t2t file in t/data/marks/ and compare with ok/*.html

my $bin     = File::Spec->catfile(dirname(__FILE__), '..', 'bin', 'txt2tags');
my $data    = File::Spec->catfile(dirname(__FILE__), 'data', 'marks');
my $ok_dir  = File::Spec->catfile($data, 'ok');

my @t2t_files = sort glob(File::Spec->catfile($data, '*.t2t'));

plan tests => scalar @t2t_files;

for my $t2t (@t2t_files) {
    my $base     = basename($t2t, '.t2t');
    my $expected = File::Spec->catfile($ok_dir, "$base.html");

    SKIP: {
        skip "No expected output file for $base", 1 unless -f $expected;

        # Run txt2tags, capture output to stdout
        my ($got, $err);
        {
            my $err_fh = gensym;
            my $pid = open3(my $in, my $out_fh, $err_fh,
                $^X, "-I" . File::Spec->catfile(dirname(__FILE__), '..', 'lib'),
                $bin, '-t', 'html', '-o', '-', $t2t);
            close $in;
            local $/;
            $got = <$out_fh>;
            $err = <$err_fh>;
            waitpid $pid, 0;
        }

        # Normalize the trailing cmdline comment (differs between implementations)
        my $norm_re = qr/<!-- cmdline:.*?-->/;
        $got =~ s/$norm_re/<!-- cmdline: NORMALIZED -->/g;

        my $exp_raw = do { local $/; open(my $fh, '<', $expected) or die $!; <$fh> };
        $exp_raw =~ s/$norm_re/<!-- cmdline: NORMALIZED -->/g;

        is($got, $exp_raw, "$base.t2t matches expected HTML");
    }
}
