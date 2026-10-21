// Minimal CLI for the Rust txt2tags prototype: reads a .t2t file, writes
// HTML or LaTeX.
//   txt2tags [-t html|tex] <input.t2t> [output-file]

use std::env;
use std::fs;
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();

    let mut target = "html";
    let mut rest: Vec<&str> = Vec::new();
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "-t" | "--target" => {
                i += 1;
                match args.get(i) {
                    Some(t) => target = t.as_str(),
                    None => {
                        eprintln!("error: -t requires an argument (html or tex)");
                        return ExitCode::FAILURE;
                    }
                }
            }
            other => rest.push(other),
        }
        i += 1;
    }

    let Some(infile) = rest.first() else {
        eprintln!("usage: txt2tags [-t html|tex] <input.t2t> [output-file]");
        return ExitCode::FAILURE;
    };

    let content = match fs::read_to_string(infile) {
        Ok(c) => c,
        Err(err) => {
            eprintln!("error: {err}");
            return ExitCode::FAILURE;
        }
    };

    let output = match target {
        "html" => txt2tags::to_html(&content),
        "tex" | "latex" => txt2tags::to_latex(&content),
        other => {
            eprintln!("error: unknown target '{other}' (expected html or tex)");
            return ExitCode::FAILURE;
        }
    };

    match rest.get(1) {
        Some(outfile) => {
            if let Err(err) = fs::write(outfile, output) {
                eprintln!("error: {err}");
                return ExitCode::FAILURE;
            }
        }
        None => println!("{output}"),
    }

    ExitCode::SUCCESS
}
