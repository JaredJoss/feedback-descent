from __future__ import annotations

from abc import ABC, abstractmethod


class SVGRenderer(ABC):
    @abstractmethod
    async def render(self, svg_code: str, width: int, height: int) -> bytes:
        """Render SVG code to PNG bytes."""
        ...


class ResvgRenderer(SVGRenderer):
    async def render(self, svg_code: str, width: int, height: int) -> bytes:
        from resvg_py import svg_to_bytes

        return svg_to_bytes(
            svg_string=svg_code,
            width=width,
            height=height,
            background="white",
        )


class PlaywrightRenderer(SVGRenderer):
    async def render(self, svg_code: str, width: int, height: int) -> bytes:
        from playwright.async_api import async_playwright

        html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:white;">
{svg_code}
</body></html>"""

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": width, "height": height})
            await page.set_content(html)
            png = await page.screenshot(type="png")
            await browser.close()
        return png


def create_renderer(name: str = "resvg") -> SVGRenderer:
    renderers = {
        "resvg": ResvgRenderer,
        "playwright": PlaywrightRenderer,
    }
    if name not in renderers:
        raise ValueError(f"Unknown renderer: {name!r}. Choose from: {list(renderers)}")
    return renderers[name]()
