-- This filter Help us to convert pandoc markup styles to word styles
-- Converts Pandoc BlockQuote elements into Word 'Block Quote' style paragraphs
-- To use this filter, include it in your Pandoc command with the --lua-filter option to use this filter
-- Example: pandoc input.md --lua-filter=blockquote.lua -o output.docx --reference-doc=reference.docx
function BlockQuote(elem)
  return pandoc.Div(elem.content, {["custom-style"] = "Block Quote"})
end

