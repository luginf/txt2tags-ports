package Text::Txt2tags::Rules;

# txt2tags - syntax rules (boolean flags) per output target
# Port of txt2tags3_mod/rules.py to Perl 5

use strict;
use warnings;
use Exporter 'import';

our $VERSION = '3.9.0';

# ---------------------------------------------------------------------------
# Full list of rule keys (all default to 0/undef unless set)
# ---------------------------------------------------------------------------
my @ALL_RULES = qw(
    linkable            tableable           tableonly
    spread              spreadgrid          imglinkable
    imgalignable        imgasdefterm        autonumberlist
    autonumbertitle     stylable            parainsidelist
    compactlist         spacedlistitem      listnotnested
    listitemnotnested   quotenotnested      verbblocknotescaped
    verbblockfinalescape escapeurl          labelbeforelink
    onelinepara         onelinequote        notbreaklistitemclose
    tabletitlerowinbold tablecellstrip      tablecellspannable
    tablecellcovered    tablecellmulticol   tablecolumnsnumber
    tablenumber         barinsidequote      finalescapetitle
    autotocnewpagebefore autotocnewpageafter autotocwithbars
    plaintexttoc        mapbar2pagebreak    titleblocks
    listlineafteropen   escapexmlchars      listlevelzerobased
    zerodepthparagraph  cellspancumulative  keepblankheaderline
    confdependenttags   confdependentrules
    indentverbblock     breaktablecell      breaktablelineopen
    notbreaklistopen    keepquoteindent     keeplistindent
    blankendautotoc     tagnotindentable    spacedlistitemopen
    spacednumlistitemopen deflisttextstrip  blanksaroundpara
    blanksaroundverb    blanksaroundquote   blanksaroundlist
    blanksaroundnumlist blanksarounddeflist blanksaroundnestedlist
    blanksaroundtable   blanksaroundbar     blanksaroundtitle
    blanksaroundnumtitle iswrapped
    listmaxdepth        quotemaxdepth       tablecellaligntype
    blockdepthmultiply  depthmultiplyplus   cellspanmultiplier
    spreadmarkup
);

# ---------------------------------------------------------------------------
# Per-target rule banks
# ---------------------------------------------------------------------------

my %HTML_RULES = (
    escapexmlchars    => 1,
    indentverbblock   => 1,
    linkable          => 1,
    stylable          => 1,
    escapeurl         => 1,
    imglinkable       => 1,
    imgalignable      => 1,
    imgasdefterm      => 1,
    autonumberlist    => 1,
    spacedlistitem    => 1,
    parainsidelist    => 1,
    tableable         => 1,
    tablecellstrip    => 1,
    breaktablecell    => 1,
    breaktablelineopen=> 1,
    keeplistindent    => 1,
    keepquoteindent   => 1,
    barinsidequote    => 1,
    autotocwithbars   => 1,
    tablecellspannable=> 1,
    tablecellaligntype=> 'cell',
    blanksaroundverb  => 1,
    blanksaroundlist  => 1,
    blanksaroundnumlist  => 1,
    blanksarounddeflist  => 1,
    blanksaroundtable => 1,
    blanksaroundbar   => 1,
    blanksaroundtitle => 1,
    blanksaroundnumtitle => 1,
);

my %RULES_BANK = (
    txt => {
        indentverbblock   => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        keeplistindent    => 1,
        barinsidequote    => 1,
        autotocwithbars   => 1,
        plaintexttoc      => 1,
        blanksaroundpara  => 1,
        blanksaroundverb  => 1,
        blanksaroundquote => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundbar   => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        iswrapped         => 1,
    },
    txt2t => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        imgasdefterm      => 1,
        autonumberlist    => 1,
        autonumbertitle   => 1,
        stylable          => 1,
        spacedlistitem    => 1,
        labelbeforelink   => 1,
        tablecellstrip    => 1,
        tablecellspannable=> 1,
        keepblankheaderline => 1,
        barinsidequote    => 1,
        keeplistindent    => 1,
        blankendautotoc   => 1,
        blanksaroundpara  => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellaligntype=> 'cell',
    },
    rst => {
        indentverbblock   => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        keeplistindent    => 1,
        barinsidequote    => 1,
        imgalignable      => 1,
        imglinkable       => 1,
        tableable         => 1,
        blanksaroundpara  => 1,
        blanksaroundverb  => 1,
        blanksaroundquote => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundbar   => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        blanksaroundnestedlist => 1,
    },
    aat  => {},   # inherits txt rules
    csv  => { tableable => 1, tableonly => 1, tablecellstrip => 1 },
    csvs => { tableable => 1, tableonly => 1, tablecellstrip => 1, spread => 1, spreadmarkup => 'txt' },
    db   => { tableable => 1, tableonly => 1 },
    ods  => {
        escapexmlchars    => 1,
        tableable         => 1,
        tableonly         => 1,
        tablecellstrip    => 1,
        tablecellspannable=> 1,
        tablecellcovered  => 1,
        tablecellaligntype=> 'cell',
    },
    html  => { %HTML_RULES },
    xhtml => { %HTML_RULES },   # inherits html
    wp    => {
        %HTML_RULES,
        onelinepara       => 1,
        onelinequote      => 1,
        tagnotindentable  => 1,
        blanksaroundpara  => 1,
        quotemaxdepth     => 1,
        keepquoteindent   => 0,
        keeplistindent    => 0,
        notbreaklistitemclose => 1,
    },
    xhtmls => { %HTML_RULES },
    html5  => { %HTML_RULES, titleblocks => 1 },
    htmls  => { %HTML_RULES, tableonly => 1, spread => 1, spreadgrid => 1, spreadmarkup => 'html' },
    sgml => {
        escapexmlchars    => 1,
        linkable          => 1,
        escapeurl         => 1,
        autonumberlist    => 1,
        spacedlistitem    => 1,
        tableable         => 1,
        tablecellstrip    => 1,
        blankendautotoc   => 1,
        keeplistindent    => 1,
        keepquoteindent   => 1,
        barinsidequote    => 1,
        finalescapetitle  => 1,
        tablecellaligntype=> 'column',
        blanksaroundpara  => 1,
        blanksaroundverb  => 1,
        blanksaroundquote => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundbar   => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        quotemaxdepth     => 1,
    },
    dbk => {
        escapexmlchars    => 1,
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        imgalignable      => 1,
        autonumberlist    => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        tablecellstrip    => 1,
        barinsidequote    => 1,
        titleblocks       => 1,
        blanksaroundpara  => 1,
        blanksaroundverb  => 1,
        blanksaroundquote => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundbar   => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
    },
    tex => {
        escapexmlchars    => 0,
        linkable          => 1,
        autonumbertitle   => 1,
        autonumberlist    => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        tableable         => 1,
        tablecellstrip    => 1,
        verbblocknotescaped => 1,
        barinsidequote    => 1,
        finalescapetitle  => 1,
        blanksaroundpara  => 1,
        blanksaroundverb  => 1,
        blanksaroundquote => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundbar   => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
    },
    texs => {
        tableable         => 1,
        tableonly         => 1,
        spread            => 1,
        spreadmarkup      => 'tex',
    },
    lout => {
        linkable          => 1,
        autonumberlist    => 1,
        spacedlistitem    => 1,
        tableable         => 1,
        tablecellstrip    => 1,
        verbblockfinalescape => 1,
        barinsidequote    => 1,
        finalescapetitle  => 1,
        blanksaroundpara  => 1,
        blanksaroundverb  => 1,
        blanksaroundquote => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundbar   => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
    },
    man => {
        linkable          => 1,
        spacedlistitem    => 1,
        tableable         => 1,
        tablecellstrip    => 1,
        verbblocknotescaped => 1,
        indentverbblock   => 0,
        barinsidequote    => 1,
        blanksaroundpara  => 1,
        blanksaroundverb  => 1,
        blanksaroundquote => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundbar   => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
    },
    mgp => {
        linkable          => 1,
        spacedlistitem    => 1,
        barinsidequote    => 1,
        mapbar2pagebreak  => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
    },
    wiki => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        imgalignable      => 1,
        spacedlistitem    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
    },
    gwiki => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        spacedlistitem    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
        listnotnested     => 1,
    },
    doku => {
        linkable          => 1,
        tableable         => 1,
        imgalignable      => 1,
        imglinkable       => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
        tablecellaligntype=> 'cell',
    },
    pmw => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
    },
    moin => {
        linkable          => 1,
        tableable         => 1,
        imgalignable      => 1,
        imglinkable       => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
        tablecellaligntype=> 'cell',
    },
    adoc => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        imgalignable      => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        blanksaroundpara  => 1,
        blanksaroundverb  => 1,
        blanksaroundquote => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundbar   => 1,
        tablecellstrip    => 1,
    },
    md => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        imgalignable      => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        barinsidequote    => 1,
        blanksaroundpara  => 1,
        blanksaroundverb  => 1,
        blanksaroundquote => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksarounddeflist  => 1,
        blanksaroundtable => 1,
        blanksaroundbar   => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
    },
    gmi => {
        linkable          => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        blanksaroundpara  => 1,
    },
    bbcode => {
        linkable          => 1,
        imglinkable       => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        blanksaroundpara  => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
    },
    creole => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        spacedlistitem    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
    },
    red => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        spacedlistitem    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
    },
    spip => {
        linkable          => 1,
        tableable         => 1,
        spacedlistitem    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
    },
    tml => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        spacedlistitem    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
    },
    vimwiki => {
        linkable          => 1,
        tableable         => 1,
        imglinkable       => 1,
        spacedlistitem    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
        tablecellstrip    => 1,
    },
    rtf => {
        linkable          => 1,
        spacedlistitem    => 1,
        parainsidelist    => 1,
        barinsidequote    => 1,
        blanksaroundpara  => 1,
        blanksaroundlist  => 1,
        blanksaroundnumlist  => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
    },
    pm6 => {
        linkable          => 1,
        spacedlistitem    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
    },
    mom => {
        linkable          => 1,
        spacedlistitem    => 1,
        tableable         => 1,
        tablecellstrip    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
    },
    utmac => {
        linkable          => 1,
        tableable         => 1,
        tablecellstrip    => 1,
        barinsidequote    => 1,
        blanksaroundtitle => 1,
        blanksaroundnumtitle => 1,
    },
);

# aat inherits txt
$RULES_BANK{aat} = { %{ $RULES_BANK{txt} } };

# ---------------------------------------------------------------------------
# getRules($config) → hashref of rule values for the given target
# ---------------------------------------------------------------------------

sub getRules {
    my ($config) = @_;
    my $target = $config->{target} or return {};

    # Normalise alias targets
    my %alias = (
        aap  => 'aat', aas  => 'aat', aatw => 'aat',
        aapw => 'aat', aasw => 'aat', aapp => 'aat',
    );
    $target = $alias{$target} if exists $alias{$target};

    # Start from the target's own bank (or empty if unknown)
    my %ret = %{ $RULES_BANK{$target} // {} };

    # Fill in every key that is not already set with 0 (integer rules)
    # or undef (string rules)
    for my $rule (@ALL_RULES) {
        $ret{$rule} //= 0 unless $rule =~ /type|markup/;
    }

    return \%ret;
}

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
our @EXPORT_OK = qw(getRules);

1;
__END__

=head1 NAME

Text::Txt2tags::Rules - Per-target syntax rules for Text::Txt2tags

=head1 SYNOPSIS

  use Text::Txt2tags::Rules qw(getRules);
  my $rules = getRules({ target => 'html' });
  if ($rules->{linkable}) { ... }

=cut
