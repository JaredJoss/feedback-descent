import pytest

from feedback_descent.domains.svg.parser import extract_svg


class TestExtractSvg:
    def test_fenced_svg_block(self):
        response = """Here's the SVG:

```svg
<svg width="100" height="100">
  <circle cx="50" cy="50" r="40" fill="red"/>
</svg>
```

Hope you like it!"""
        result = extract_svg(response)
        assert "<svg" in result
        assert "<circle" in result

    def test_fenced_xml_block(self):
        response = """```xml
<svg width="200" height="200">
  <rect width="100" height="100" fill="blue"/>
</svg>
```"""
        result = extract_svg(response)
        assert "<svg" in result
        assert "<rect" in result

    def test_generic_fenced_block(self):
        response = """```
<svg width="100" height="100">
  <line x1="0" y1="0" x2="100" y2="100" stroke="black"/>
</svg>
```"""
        result = extract_svg(response)
        assert "<svg" in result

    def test_raw_svg(self):
        response = """<svg width="100" height="100"><circle cx="50" cy="50" r="25" fill="green"/></svg>"""
        result = extract_svg(response)
        assert "<svg" in result
        assert 'fill="green"' in result

    def test_svg_with_surrounding_text(self):
        response = """I've created an SVG for you.

<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512">
  <rect width="512" height="512" fill="#f0f0f0"/>
  <circle cx="256" cy="256" r="100" fill="coral"/>
</svg>

This SVG shows a coral circle on a gray background."""
        result = extract_svg(response)
        assert 'xmlns="http://www.w3.org/2000/svg"' in result

    def test_no_svg_raises(self):
        with pytest.raises(ValueError, match="No valid SVG found"):
            extract_svg("This response has no SVG at all.")

    def test_empty_fence_no_svg_raises(self):
        with pytest.raises(ValueError, match="No valid SVG found"):
            extract_svg("```svg\njust some text\n```")

    def test_multiline_svg(self):
        response = """```svg
<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
      <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="400" height="400" fill="url(#grad1)" />
</svg>
```"""
        result = extract_svg(response)
        assert "linearGradient" in result
        assert "url(#grad1)" in result
