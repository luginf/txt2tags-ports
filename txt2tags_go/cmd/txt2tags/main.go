// Command line of the Go txt2tags port. It follows the options of the
// Python port (txt2tags3_mod) that make sense for the three targets of this
// port (html, tex, md); the options that need machinery this port does not
// have (CSS, templates, rc files, other targets...) are refused with a clear
// error instead of being silently ignored.
//
//	txt2tags [OPTIONS] [infile.t2t]      (try --help)
package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"

	"txt2tags"
)

const version = "1.1.0"

type optSpec struct {
	long    string
	short   rune // 0 = none
	takeArg bool
}

var known = []optSpec{
	{"targets", 0, false},
	{"target", 't', true},
	{"infile", 'i', true},
	{"outfile", 'o', true},
	{"encoding", 0, true},
	{"toc", 0, false},
	{"toc-title", 0, true},
	{"toc-level", 0, true},
	{"toc-only", 0, false},
	{"enum-title", 'n', false},
	{"skip-header-lines", 0, false},
	{"legacy", 0, false},
	{"blank-closes-list", 0, false},
	{"headers", 0, false},
	{"quiet", 'q', false},
	{"verbose", 'v', false},
	{"help", 'h', false},
	{"version", 'V', false},
	{"dump-config", 0, false},
	{"dump-source", 0, false},
	{"no-rc", 0, false},
}

// Python options this port cannot honour.
var unsupported = []optSpec{
	{"style", 0, true},
	{"css-sugar", 0, false},
	{"css-inside", 0, false},
	{"embed-images", 0, false},
	{"template", 'T', true},
	{"mask-email", 0, false},
	{"width", 0, true},
	{"height", 0, true},
	{"chars", 0, true},
	{"config-file", 'C', true},
	{"fix-path", 0, false},
	{"gui", 0, false},
}

var targetGroups = []struct {
	group   string
	targets [][2]string
}{
	{"HTML", [][2]string{{"html", "HTML page"}}},
	{"WIKI", [][2]string{{"md", "Markdown document"}}},
	{"OFFICE", [][2]string{{"tex", "LaTeX document"}}},
}

const help = `Usage: txt2tags [OPTIONS] [infile.t2t]

      --targets       print a list of all the available targets and exit
  -t, --target=TYPE   set target document type. currently supported:
                      html, md, tex
  -i, --infile=FILE   set FILE as the input file name ('-' for STDIN)
  -o, --outfile=FILE  set FILE as the output file name ('-' for STDOUT)
      --encoding=ENC  inform source file encoding (only UTF-8 is supported)
      --toc           add an automatic Table of Contents to the output
      --toc-title=S   set custom TOC title to S
      --toc-level=N   set maximum TOC level (depth) to N (default 3)
      --toc-only      print the Table of Contents and exit (html, md)
  -n, --enum-title    enumerate all titles as 1, 1.1, 1.1.1, etc (html, md)
      --skip-header-lines don't reserve the first 3 lines for title/author/date:
                      the document body starts on line 1
      --blank-closes-list, --legacy
                      accepted for compatibility, no effect: a title always
                      ends a list in this port
  -H, --no-headers    suppress header and footer from the output
  -q, --quiet         quiet mode, suppress all output (except errors)
  -v, --verbose       accepted for compatibility
  -h, --help          print this help information and exit
  -V, --version       print program version and exit
      --dump-config   print all the configuration found and exit
      --dump-source   print the document source and exit
      --no-rc         accepted for compatibility (rc files are never read)

Not supported by this port (use the Python or Perl port): --style, --css-sugar,
--css-inside, --embed-images, -T/--template, --mask-email, --width, --height,
--chars, -C/--config-file, --fix-path, --gui.

Example:
     txt2tags -t html --toc file.t2t

The 'no-' prefix disables the option:
     --no-toc, --no-enum-title, ...

By default, converted output is saved to 'infile.<target>'.
Use --outfile to force an output file name.
If  input file is '-', reads from STDIN.
If output file is '-', dumps output to STDOUT.

http://txt2tags.org
`

type cli struct {
	opts       txt2tags.Options
	target     string
	hasTarget  bool
	infile     string
	hasInfile  bool
	outfile    string
	hasOutfile bool
	quiet      bool
	help       bool
	version    bool
	targets    bool
	dumpConfig bool
	dumpSource bool
	positional []string
	seen       map[string]string // options as given, for --dump-config
}

func onOff(negate bool) string {
	if negate {
		return "OFF"
	}
	return "ON"
}

func (c *cli) set(name string, negate bool, value *string) error {
	val := ""
	if value != nil {
		val = *value
	}
	switch name {
	case "targets":
		c.targets = !negate
	case "target":
		c.target, c.hasTarget = val, !negate
	case "infile":
		c.infile, c.hasInfile = val, !negate
	case "outfile":
		c.outfile, c.hasOutfile = val, !negate
	case "encoding":
		e := strings.ReplaceAll(strings.ToLower(val), "_", "-")
		if !negate && e != "utf-8" && e != "utf8" {
			return fmt.Errorf("unsupported encoding '%s': this port only reads UTF-8", val)
		}
	case "toc":
		c.opts.Toc = !negate
	case "toc-title":
		c.opts.TocTitle = val
		if negate {
			c.opts.TocTitle = ""
		}
	case "toc-level":
		c.opts.TocLevel = 0
		if !negate {
			n, err := strconv.Atoi(val)
			if err != nil || n < 1 {
				return fmt.Errorf("--toc-level needs a number, got '%s'", val)
			}
			c.opts.TocLevel = n
		}
	case "toc-only":
		c.opts.TocOnly = !negate
	case "enum-title":
		c.opts.EnumTitle = !negate
	case "skip-header-lines":
		c.opts.SkipHeaderLines = !negate
	case "headers": // --no-headers is -H: the option itself is "headers"
		c.opts.NoHeaders = negate
	case "quiet":
		c.quiet = !negate
	case "help":
		c.help = !negate
	case "version":
		c.version = !negate
	case "dump-config":
		c.dumpConfig = !negate
	case "dump-source":
		c.dumpSource = !negate
	case "legacy", "blank-closes-list", "verbose", "no-rc":
		// accepted, nothing to do
	default:
		return fmt.Errorf("unrecognized option: %s", name)
	}
	shown := onOff(negate)
	if value != nil {
		shown = val
	}
	c.seen[name] = shown
	return nil
}

func findLong(list []optSpec, name string) (optSpec, bool) {
	for _, o := range list {
		if o.long == name {
			return o, true
		}
	}
	return optSpec{}, false
}

func findShort(list []optSpec, r rune) (optSpec, bool) {
	for _, o := range list {
		if o.short == r {
			return o, true
		}
	}
	return optSpec{}, false
}

func parseArgs(args []string) (*cli, error) {
	c := &cli{seen: map[string]string{}}
	for i := 0; i < len(args); i++ {
		a := args[i]
		switch {
		case a == "--":
			c.positional = append(c.positional, args[i+1:]...)
			return c, nil
		case strings.HasPrefix(a, "--"):
			name, inline, hasInline := strings.Cut(a[2:], "=")
			base, negate := name, false
			if name == "no-headers" {
				base, negate = "headers", true
			} else if name != "no-rc" && strings.HasPrefix(name, "no-") {
				base, negate = name[3:], true
			}
			if _, ok := findLong(unsupported, base); ok {
				return nil, fmt.Errorf("option --%s is not supported by this port (use the Python or Perl port)", base)
			}
			spec, ok := findLong(known, base)
			if !ok {
				return nil, fmt.Errorf("unrecognized option --%s (try --help)", name)
			}
			var value *string
			switch {
			case spec.takeArg && !negate:
				if hasInline {
					value = &inline
				} else {
					i++
					if i >= len(args) {
						return nil, fmt.Errorf("option --%s requires an argument", base)
					}
					value = &args[i]
				}
			case hasInline:
				return nil, fmt.Errorf("option --%s does not take an argument", base)
			}
			if err := c.set(base, negate, value); err != nil {
				return nil, err
			}
		case len(a) > 1 && a[0] == '-':
			// a cluster of short options: -nH, -thtml, -o out.html
			chars := []rune(a[1:])
			for k := 0; k < len(chars); k++ {
				ch := chars[k]
				if ch == 'H' {
					if err := c.set("headers", true, nil); err != nil {
						return nil, err
					}
					continue
				}
				if u, ok := findShort(unsupported, ch); ok {
					return nil, fmt.Errorf("option -%c (--%s) is not supported by this port (use the Python or Perl port)", ch, u.long)
				}
				spec, ok := findShort(known, ch)
				if !ok {
					return nil, fmt.Errorf("unrecognized option -%c (try --help)", ch)
				}
				if spec.takeArg {
					rest := string(chars[k+1:])
					if rest == "" {
						i++
						if i >= len(args) {
							return nil, fmt.Errorf("option -%c requires an argument", ch)
						}
						rest = args[i]
					}
					if err := c.set(spec.long, false, &rest); err != nil {
						return nil, err
					}
					break
				}
				if err := c.set(spec.long, false, nil); err != nil {
					return nil, err
				}
			}
		default:
			c.positional = append(c.positional, a)
		}
	}
	return c, nil
}

func defaultOutfile(infile, ext string) string {
	if strings.EqualFold(filepath.Ext(infile), ".t2t") {
		return infile[:len(infile)-len(filepath.Ext(infile))] + "." + ext
	}
	return infile + "." + ext
}

func readInput(infile string) (string, error) {
	var data []byte
	var err error
	if infile == "-" {
		data, err = io.ReadAll(os.Stdin)
		if err != nil {
			return "", fmt.Errorf("cannot read STDIN: %v", err)
		}
	} else if data, err = os.ReadFile(infile); err != nil {
		return "", fmt.Errorf("cannot read file: %s: %v", infile, err)
	}
	if !utf8.Valid(data) {
		return "", fmt.Errorf("%s is not valid UTF-8 (this port only reads UTF-8)", infile)
	}
	return string(data), nil
}

func fail(err error) {
	fmt.Fprintf(os.Stderr, "txt2tags: Error: %v\n", err)
	os.Exit(1)
}

func main() {
	c, err := parseArgs(os.Args[1:])
	if err != nil {
		fail(err)
	}

	if c.help {
		fmt.Print(help)
		return
	}
	if c.version {
		fmt.Printf("txt2tags version %s (Go port). <http://txt2tags.org>\n", version)
		return
	}
	if c.targets {
		for _, g := range targetGroups {
			fmt.Printf("%s:\n", g.group)
			for _, t := range g.targets {
				fmt.Printf("\t%s\t%s\n", t[0], t[1])
			}
			fmt.Println()
		}
		return
	}

	// -i/--infile wins; otherwise the first positional is the input file
	// and, as before this port had options, a second one is the output file.
	positional := c.positional
	next := func() (string, bool) {
		if len(positional) == 0 {
			return "", false
		}
		v := positional[0]
		positional = positional[1:]
		return v, true
	}
	infile := c.infile
	if !c.hasInfile {
		var ok bool
		if infile, ok = next(); !ok {
			fail(fmt.Errorf("Missing input file (try --help)\n\nPlease inform an input file (.t2t) at the end of the command.\nExample: txt2tags -t html file.t2t"))
		}
	}
	if !c.hasOutfile {
		if f, ok := next(); ok {
			c.outfile, c.hasOutfile = f, true
		}
	}
	if extra, ok := next(); ok {
		fail(fmt.Errorf("unexpected extra argument: %s", extra))
	}

	targetName := "html"
	if c.hasTarget {
		targetName = c.target
	}
	target, ok := txt2tags.TargetFromName(targetName)
	if !ok {
		fail(fmt.Errorf("invalid target '%s' (this port supports html, md, tex; see --targets)", targetName))
	}

	source, err := readInput(infile)
	if err != nil {
		fail(err)
	}

	if c.dumpSource {
		fmt.Print(source)
		if !strings.HasSuffix(source, "\n") {
			fmt.Println()
		}
		return
	}
	if c.dumpConfig {
		fmt.Println("Full PARSED config")
		fmt.Printf("      infile........: %s\n", infile)
		fmt.Printf("      target........: %s\n", target.Name())
		keys := make([]string, 0, len(c.seen))
		for k := range c.seen {
			if k != "infile" && k != "target" && k != "dump-config" {
				keys = append(keys, k)
			}
		}
		sort.Strings(keys)
		for _, k := range keys {
			dots := 14 - len(k)
			if dots < 1 {
				dots = 1
			}
			fmt.Printf("      %s%s: %s\n", k, strings.Repeat(".", dots), c.seen[k])
		}
		return
	}

	outfile := c.outfile
	switch {
	case c.hasOutfile:
	case infile == "-":
		outfile = "-"
	default:
		outfile = defaultOutfile(infile, target.Extension())
	}
	c.opts.Infile, c.opts.Outfile = infile, outfile
	output, err := txt2tags.Convert(source, target, c.opts)
	if err != nil {
		fail(err)
	}
	// like the Python port, an empty result is written as nothing at all
	if output != "" {
		output += "\n"
	}
	if outfile == "-" {
		fmt.Print(output)
		return
	}
	if err := os.WriteFile(outfile, []byte(output), 0o644); err != nil {
		fail(fmt.Errorf("cannot open file for writing: %s: %v", outfile, err))
	}
	if !c.quiet {
		fmt.Printf("txt2tags wrote %s\n", outfile)
	}
}
