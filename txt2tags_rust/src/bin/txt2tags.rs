// Command line of the Rust txt2tags port. It follows the options of the
// Python port (txt2tags3_mod) that make sense for the three targets of this
// port (html, tex, md); the options that need machinery this port does not
// have (CSS, templates, rc files, other targets...) are refused with a clear
// error instead of being silently ignored.
//
//   txt2tags [OPTIONS] [infile.t2t]      (try --help)

use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::io::{self, Read};
use std::path::Path;
use std::process::ExitCode;

use txt2tags::{convert, Options, Target};

const VERSION: &str = "1.1.0";

/// (long name, short name, takes an argument)
const KNOWN: &[(&str, Option<char>, bool)] = &[
    ("targets", None, false),
    ("target", Some('t'), true),
    ("infile", Some('i'), true),
    ("outfile", Some('o'), true),
    ("encoding", None, true),
    ("toc", None, false),
    ("toc-title", None, true),
    ("toc-level", None, true),
    ("toc-only", None, false),
    ("enum-title", Some('n'), false),
    ("skip-header-lines", None, false),
    ("legacy", None, false),
    ("blank-closes-list", None, false),
    ("headers", None, false),
    ("quiet", Some('q'), false),
    ("verbose", Some('v'), false),
    ("help", Some('h'), false),
    ("version", Some('V'), false),
    ("dump-config", None, false),
    ("dump-source", None, false),
    ("no-rc", None, false),
];

/// Python options this port cannot honour: (long name, short name, takes an argument)
const UNSUPPORTED: &[(&str, Option<char>, bool)] = &[
    ("style", None, true),
    ("css-sugar", None, false),
    ("css-inside", None, false),
    ("embed-images", None, false),
    ("template", Some('T'), true),
    ("mask-email", None, false),
    ("width", None, true),
    ("height", None, true),
    ("chars", None, true),
    ("config-file", Some('C'), true),
    ("fix-path", None, false),
    ("gui", None, false),
];

const TARGET_GROUPS: &[(&str, &[(&str, &str)])] = &[
    ("HTML", &[("html", "HTML page")]),
    ("WIKI", &[("md", "Markdown document")]),
    ("OFFICE", &[("tex", "LaTeX document")]),
];

const HELP: &str = "Usage: txt2tags [OPTIONS] [infile.t2t]

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
";

fn fail(msg: &str) -> ExitCode {
    eprintln!("txt2tags: Error: {msg}");
    ExitCode::FAILURE
}

#[derive(Default)]
struct Cli {
    opts: Options,
    target: Option<String>,
    infile: Option<String>,
    outfile: Option<String>,
    quiet: bool,
    help: bool,
    version: bool,
    targets: bool,
    dump_config: bool,
    dump_source: bool,
    positional: Vec<String>,
    /// options as given, for --dump-config
    seen: BTreeMap<String, String>,
}

fn on_off(negate: bool) -> String {
    if negate { "OFF" } else { "ON" }.to_string()
}

impl Cli {
    fn set(&mut self, name: &str, negate: bool, value: Option<String>) -> Result<(), String> {
        let val = value.clone().unwrap_or_default();
        match name {
            "targets" => self.targets = !negate,
            "target" => self.target = if negate { None } else { Some(val.clone()) },
            "infile" => self.infile = if negate { None } else { Some(val.clone()) },
            "outfile" => self.outfile = if negate { None } else { Some(val.clone()) },
            "encoding" => {
                let e = val.to_lowercase().replace('_', "-");
                if !negate && e != "utf-8" && e != "utf8" {
                    return Err(format!(
                        "unsupported encoding '{val}': this port only reads UTF-8"
                    ));
                }
            }
            "toc" => self.opts.toc = !negate,
            "toc-title" => self.opts.toc_title = if negate { String::new() } else { val.clone() },
            "toc-level" => {
                self.opts.toc_level = if negate {
                    None
                } else {
                    match val.parse::<usize>() {
                        Ok(n) if n >= 1 => Some(n),
                        _ => return Err(format!("--toc-level needs a number, got '{val}'")),
                    }
                }
            }
            "toc-only" => self.opts.toc_only = !negate,
            "enum-title" => self.opts.enum_title = !negate,
            "skip-header-lines" => self.opts.skip_header_lines = !negate,
            // --no-headers is -H: the option itself is "headers"
            "headers" => self.opts.no_headers = negate,
            "quiet" => self.quiet = !negate,
            "help" => self.help = !negate,
            "version" => self.version = !negate,
            "dump-config" => self.dump_config = !negate,
            "dump-source" => self.dump_source = !negate,
            // accepted, nothing to do
            "legacy" | "blank-closes-list" | "verbose" | "no-rc" => {}
            other => return Err(format!("unrecognized option: {other}")),
        }
        let shown = match value {
            Some(v) => v,
            None => on_off(negate),
        };
        self.seen.insert(name.to_string(), shown);
        Ok(())
    }

    fn parse(args: &[String]) -> Result<Cli, String> {
        let mut cli = Cli::default();
        let mut i = 0;
        while i < args.len() {
            let a = &args[i];
            if a == "--" {
                cli.positional.extend(args[i + 1..].iter().cloned());
                break;
            } else if let Some(long) = a.strip_prefix("--") {
                let (name, inline) = match long.split_once('=') {
                    Some((n, v)) => (n, Some(v.to_string())),
                    None => (long, None),
                };
                let (base, negate) = if name == "no-headers" {
                    ("headers", true)
                } else if name != "no-rc" && name.starts_with("no-") {
                    (&name[3..], true)
                } else {
                    (name, false)
                };
                if UNSUPPORTED.iter().any(|u| u.0 == base) {
                    return Err(format!(
                        "option --{base} is not supported by this port (use the Python or Perl port)"
                    ));
                }
                let Some(&(_, _, takes)) = KNOWN.iter().find(|k| k.0 == base) else {
                    return Err(format!("unrecognized option --{name} (try --help)"));
                };
                let value = if takes && !negate {
                    match inline {
                        Some(v) => Some(v),
                        None => {
                            i += 1;
                            Some(
                                args.get(i)
                                    .ok_or_else(|| format!("option --{base} requires an argument"))?
                                    .clone(),
                            )
                        }
                    }
                } else if inline.is_some() {
                    return Err(format!("option --{base} does not take an argument"));
                } else {
                    None
                };
                cli.set(base, negate, value)?;
            } else if a.len() > 1 && a.starts_with('-') {
                // a cluster of short options: -nH, -thtml, -o out.html
                let chars: Vec<char> = a[1..].chars().collect();
                let mut k = 0;
                while k < chars.len() {
                    let c = chars[k];
                    if c == 'H' {
                        cli.set("headers", true, None)?;
                        k += 1;
                        continue;
                    }
                    if let Some(u) = UNSUPPORTED.iter().find(|u| u.1 == Some(c)) {
                        return Err(format!(
                            "option -{c} (--{}) is not supported by this port (use the Python or Perl port)",
                            u.0
                        ));
                    }
                    let Some(&(name, _, takes)) = KNOWN.iter().find(|k| k.1 == Some(c)) else {
                        return Err(format!("unrecognized option -{c} (try --help)"));
                    };
                    if takes {
                        let rest: String = chars[k + 1..].iter().collect();
                        let value = if !rest.is_empty() {
                            rest
                        } else {
                            i += 1;
                            args.get(i)
                                .ok_or_else(|| format!("option -{c} requires an argument"))?
                                .clone()
                        };
                        cli.set(name, false, Some(value))?;
                        break;
                    }
                    cli.set(name, false, None)?;
                    k += 1;
                }
            } else {
                cli.positional.push(a.clone());
            }
            i += 1;
        }
        Ok(cli)
    }
}

fn default_outfile(infile: &str, ext: &str) -> String {
    let path = Path::new(infile);
    let is_t2t = path
        .extension()
        .map_or(false, |e| e.eq_ignore_ascii_case("t2t"));
    if is_t2t {
        path.with_extension(ext).to_string_lossy().into_owned()
    } else {
        format!("{infile}.{ext}")
    }
}

fn read_input(infile: &str) -> Result<String, String> {
    let bytes = if infile == "-" {
        let mut buf = Vec::new();
        io::stdin()
            .read_to_end(&mut buf)
            .map_err(|e| format!("cannot read STDIN: {e}"))?;
        buf
    } else {
        fs::read(infile).map_err(|e| format!("cannot read file: {infile}: {e}"))?
    };
    String::from_utf8(bytes).map_err(|_| {
        format!("{infile} is not valid UTF-8 (this port only reads UTF-8)")
    })
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let mut cli = match Cli::parse(&args) {
        Ok(c) => c,
        Err(e) => return fail(&e),
    };

    if cli.help {
        print!("{HELP}");
        return ExitCode::SUCCESS;
    }
    if cli.version {
        println!("txt2tags version {VERSION} (Rust port). <http://txt2tags.org>");
        return ExitCode::SUCCESS;
    }
    if cli.targets {
        for (group, targets) in TARGET_GROUPS {
            println!("{group}:");
            for (name, desc) in *targets {
                println!("\t{name}\t{desc}");
            }
            println!();
        }
        return ExitCode::SUCCESS;
    }

    // -i/--infile wins; otherwise the first positional is the input file
    // and, as before this port had options, a second one is the output file.
    let mut positional = std::mem::take(&mut cli.positional).into_iter();
    let infile = match cli.infile.clone().or_else(|| positional.next()) {
        Some(f) => f,
        None => {
            return fail(
                "Missing input file (try --help)\n\nPlease inform an input file (.t2t) at the end of the command.\nExample: txt2tags -t html file.t2t",
            )
        }
    };
    if cli.outfile.is_none() {
        cli.outfile = positional.next();
    }
    if let Some(extra) = positional.next() {
        return fail(&format!("unexpected extra argument: {extra}"));
    }

    let target_name = cli.target.clone().unwrap_or_else(|| "html".to_string());
    let Some(target) = Target::from_name(&target_name) else {
        return fail(&format!(
            "invalid target '{target_name}' (this port supports html, md, tex; see --targets)"
        ));
    };

    let source = match read_input(&infile) {
        Ok(s) => s,
        Err(e) => return fail(&e),
    };

    if cli.dump_source {
        print!("{source}");
        if !source.ends_with('\n') {
            println!();
        }
        return ExitCode::SUCCESS;
    }
    if cli.dump_config {
        println!("Full PARSED config");
        println!("      infile........: {infile}");
        println!("      target........: {}", target.name());
        for (k, v) in &cli.seen {
            if k != "infile" && k != "target" && k != "dump-config" {
                println!("      {k}{}: {v}", ".".repeat(14usize.saturating_sub(k.len()).max(1)));
            }
        }
        return ExitCode::SUCCESS;
    }

    let outfile = match cli.outfile.clone() {
        Some(f) => f,
        None if infile == "-" => "-".to_string(),
        None => default_outfile(&infile, target.extension()),
    };
    cli.opts.infile = infile.clone();
    cli.opts.outfile = outfile.clone();
    let output = match convert(&source, target, &cli.opts) {
        Ok(o) => o,
        Err(e) => return fail(&e),
    };
    // like the Python port, an empty result is written as nothing at all
    let output = if output.is_empty() { output } else { format!("{output}\n") };
    if outfile == "-" {
        print!("{output}");
    } else {
        if let Err(e) = fs::write(&outfile, &output) {
            return fail(&format!("cannot open file for writing: {outfile}: {e}"));
        }
        if !cli.quiet {
            println!("txt2tags wrote {outfile}");
        }
    }
    ExitCode::SUCCESS
}
