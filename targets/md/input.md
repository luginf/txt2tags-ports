TXT2TAGS TEST INPUT
Test Suite
2026-01-01


# Level 1 Title 

## Level 2 Title 

### Level 3 Title 

#### Level 4 Title 

##### Level 5 Title 

## Inline Markup 

Normal text. **Bold text**. *Italic text*. Underline text.
~~Strikethrough~~. `Monospaced text`.

**Bold and *italic* combined**. *Italic and underline combined*.

Escaped char: \**not bold**.

## Paragraphs 

First paragraph with some content.
Still the first paragraph (line continuation).

Second paragraph after blank line.

## Horizontal Bars 

---

---

## Lists 

### Unordered List 

 * First item
 * Second item
  * Nested item A
  * Nested item B
   * Deeply nested
 * Third item

=== Ordered List ===


1. First step
1. Second step
1. Sub-step one
1. Sub-step two
1. Third step

=== Definition List ===


: Term One
Definition of term one.
: Term Two
Definition of term two.
: Term Three
A longer definition that spans
multiple source lines.

## Links 

A bare URL: http://txt2tags.org

A named link: [TXT2TAGS](http://txt2tags.org)

A local anchor link: [Introduction](#level-1-title)

## Images 

![](portrait.png)

## Verbatim Block 

    def hello(name):
        print("Hello, " + name)
    
    hello("world")

## Raw Block 

<b>This is raw HTML — passed through as-is.</b>

## Quote Block 

> Single level quote.
> Still inside the quote.
> > Nested (double) quote.

## Tables 

### Simple Table 

|col A |col B |col C|
|val 1 |val 2 |val 3|
|val 4 |val 5 |val 6|

### Table With Header 

| head 1 |head 2 |head 3|
|---------------|
|cell 1 |cell 2 |cell 3|
|cell 4 |cell 5 |cell 6|

### Aligned Table 

| Name |Age |City|
|---------------|
|Alice |30 |Paris|
|Bob |25 |Lyon|
|Charlotte |35 |Marseille|

## Special Characters 

Angle brackets: < and >
Ampersand: &
At sign: x@example.com (auto-linked email)
Percent: 50%
Backslash: \\

## Inline Verbatim 

Use `print()` to display output.
The `for` loop iterates over items.

## Multiline Verbatim 

    line one
    line two
    line three

## End of Document 

This is the last paragraph.

