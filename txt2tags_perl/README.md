# txt2tags, perl edition

This version of txt2tags has been ported to Perl with the help of LLM.

Why Perl? 

txt2tags has originally been made by Aurelio Jargas in 2001 for python 2.1

Since then, python changed a lot, going from version 2 to version 3, introducting breaking changes and the need to rewrite almost everything. The official txt2tags for python3 removed several features that I found essentials: templates, table of contents, macro and many others. Python2 is now complicated to make to work on modern distributions.

I managed to save and try to maintain a python3 version ported by Jan Max Meyer, which hasn't remove those essential features. But even an upgrade from python3.9 to python3.11 could break everything, again.

Perl is far more conservative.

This port should be complete now and similar to the python version.



