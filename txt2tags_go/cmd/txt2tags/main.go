// Minimal CLI for the Go txt2tags prototype: reads a .t2t file, writes
// HTML or LaTeX.
//
//	txt2tags [-t html|tex] <input.t2t> [output-file]
package main

import (
	"fmt"
	"os"

	"txt2tags"
)

func main() {
	args := os.Args[1:]

	target := "html"
	var rest []string
	i := 0
	for i < len(args) {
		switch args[i] {
		case "-t", "--target":
			i++
			if i >= len(args) {
				fmt.Fprintln(os.Stderr, "error: -t requires an argument (html or tex)")
				os.Exit(1)
			}
			target = args[i]
		default:
			rest = append(rest, args[i])
		}
		i++
	}

	if len(rest) < 1 {
		fmt.Fprintln(os.Stderr, "usage: txt2tags [-t html|tex] <input.t2t> [output-file]")
		os.Exit(1)
	}
	infile := rest[0]

	content, err := os.ReadFile(infile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}

	var output string
	switch target {
	case "html":
		output = txt2tags.ToHTML(string(content))
	case "tex", "latex":
		output = txt2tags.ToLatex(string(content))
	default:
		fmt.Fprintf(os.Stderr, "error: unknown target '%s' (expected html or tex)\n", target)
		os.Exit(1)
	}

	if len(rest) >= 2 {
		if err := os.WriteFile(rest[1], []byte(output), 0o644); err != nil {
			fmt.Fprintf(os.Stderr, "error: %v\n", err)
			os.Exit(1)
		}
		return
	}
	fmt.Println(output)
}
