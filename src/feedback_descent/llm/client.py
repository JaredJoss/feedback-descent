from __future__ import annotations

import base64
from dataclasses import dataclass

import litellm

litellm.drop_params = True


@dataclass
class ImageInput:
    data: bytes
    media_type: str  # e.g. "image/png"


class LLMClient:
    def __init__(self, model: str) -> None:
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 16384,
        temperature: float = 0.7,
    ) -> str:
        response = await litellm.acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def evaluate_with_images(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[ImageInput],
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        content: list[dict] = []
        for i, img in enumerate(images):
            label = "A" if i == 0 else "B"
            content.append({"type": "text", "text": f"Image {label}:"})
            b64 = base64.b64encode(img.data).decode()
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{img.media_type};base64,{b64}",
                },
            })
        content.append({"type": "text", "text": user_prompt})

        response = await litellm.acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
